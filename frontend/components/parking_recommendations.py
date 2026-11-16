import logging
from datetime import datetime
from database import database
from nicegui import run, ui
from backend.walk_time import load_buildings
from backend.algorithm_version2 import recommend_for_student
# Get the actual walking path after the student confirms a parking lot.
from backend.walking_route import get_walking_route

logger = logging.getLogger(__name__)


class ParkingRecommendations:
    """Display real recommendations; route updates and persistence are future work."""

    def __init__(self, user_id: int, map_view) -> None:
        self.user_id = user_id
        # Store the map so we can update it when a student selects a lot.
        self.map_view = map_view
        self.lot_marker = None
        # Keep track of the walking route so we can remove it when needed.
        self.route_line = None
        self.selected = None
        self.option_buttons = []
        self.recommendations = []

        with ui.column().classes('w-full gap-3'):
            with ui.row().classes('w-full items-center justify-between gap-2'):
                ui.label('Routing options').classes('serif text-2xl font-bold')
                ui.label(datetime.now().strftime('%A · %B %d')).classes('text-gray-500 text-sm')
            with ui.row().classes('items-center gap-2') as self.loading:
                ui.spinner(size='sm')
                ui.label('Finding today’s parking options…').props('role=status')
            self.status = ui.label('').classes('text-gray-600').props('role=status')
            self.status.set_visibility(False)
            self.options = ui.element('div').classes('recommendation-options')
            with ui.row().classes('w-full justify-end'):
                self.accept = ui.button('Accept', on_click=self.open_confirmation).classes(
                    'yellow-button'
                ).props('unelevated')
                self.accept.disable()

        with ui.dialog() as self.dialog, ui.card().classes('w-full max-w-md p-6 gap-4'):
            ui.label('Confirm parking selection').classes('serif text-2xl font-bold')
            self.confirmation_text = ui.label('')
            ui.label('Your parking choice will be saved when you confirm.').classes(
                'text-sm text-gray-500'
            )
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=self.dialog.close).props('flat')
                ui.button('Confirm', on_click=self.confirm_selection).classes(
                    'yellow-button'
                ).props('unelevated')

        # Start after the client connects so the map and schedule can render first.
        self.load_timer = ui.timer(0.1, self.load, once=True)

    async def load(self) -> None:
        try:
            results = await run.io_bound(recommend_for_student, self.user_id)
            if results is None:
                self.show_status('Parking recommendations are unavailable. Please try again later.', error=True)
                return
            self.recommendations = results[:3]
            if not self.recommendations:
                self.show_status('No parking recommendations for today. You may have no classes scheduled.')
                return
            with self.options:
                for index, result in enumerate(self.recommendations):
                    label = (
                        f'{index + 1}. {result["lot"]}\n'
                        f'To first class: {result["walk_to"]:.1f} min\n'
                        f'Back to parking: {result["walk_from"]:.1f} min\n'
                        f'Score: {result["score"]:.2f}'
                    )
                    button = ui.button(
                        label, on_click=lambda index=index: self.select(index)
                    ).classes('recommendation-option').props('no-caps unelevated aria-pressed=false')
                    self.option_buttons.append(button)
            self.select(0)
        except Exception:
            logger.exception('Could not load parking recommendations')
            self.show_status('Parking recommendations could not be loaded. Please try again later.', error=True)
        finally:
            self.loading.set_visibility(False)

    def show_status(self, message: str, *, error: bool = False) -> None:
        self.status.set_text(message)
        self.status.props(f'role={"alert" if error else "status"}')
        self.status.set_visibility(True)

    def select(self, index: int) -> None:
        self.selected = self.recommendations[index]
        for button_index, button in enumerate(self.option_buttons):
            selected = button_index == index
            button.classes(
                add='recommendation-option-selected' if selected else '',
                remove='' if selected else 'recommendation-option-selected',
            ).props(f'aria-pressed={str(selected).lower()}')
        self.accept.enable()
        self.update_route_preview(self.selected)

    def update_route_preview(self, recommendation: dict) -> None:
        # Remove the old walking route when the student selects another lot.
        # The new route will only appear after they confirm their selection.
        if self.route_line is not None:
            self.map_view.remove_layer(self.route_line)
            self.route_line = None
        # Find the parking lot the student selected.
        lot_name = recommendation["lot"]
        lots = database.get_all_lots()

        selected_lot = next(
            (lot for lot in lots if lot[1] == lot_name),
            None
        )

        if selected_lot is None:
            ui.notify('Parking lot location not found.', type='negative')
            return

        # Get the parking lot's coordinates from the database.
        latitude = selected_lot[2]
        longitude = selected_lot[3]

        # Remove the previous marker before showing the new selection.
        if self.lot_marker is not None:
            self.map_view.remove_layer(self.lot_marker)
            self.lot_marker = None

        # Mark the selected parking lot on the map.
        self.lot_marker = self.map_view.marker(
            latlng=(latitude, longitude)
        )

        # Move the map to the selected parking lot.
        self.map_view.set_center((latitude, longitude))

    def open_confirmation(self) -> None:
        if self.selected is None:
            return
        self.confirmation_text.set_text(f'Choose {self.selected["lot"]} for today’s parking?')
        self.dialog.open()

    def get_parking_times(self):

        # Get today's day so we only look at classes scheduled for today.
        day = datetime.now().strftime("%A")
        schedule = database.get_user_schedule_by_day(self.user_id, day)

        # Don't create a parking plan if the student has no classes today.
        if isinstance(schedule, str) or not schedule:
            return None

        # Find the earliest class and latest class using their start and end times.
        first_class = min(schedule, key=lambda row: row[5])
        last_class = max(schedule, key=lambda row: row[6])

        # Students should arrive 15 minutes before their first class.
        from datetime import timedelta

        first_start = datetime.strptime(first_class[5], "%H:%M")
        arrival = first_start - timedelta(minutes=15)

        # Students leave after their last class ends.
        departure = datetime.strptime(last_class[6], "%H:%M")

        return day, arrival.strftime("%H:%M"), departure.strftime("%H:%M")

    async def confirm_selection(self) -> None:
        if self.selected is None:
            return

        self.dialog.close()

        # Get today's parking times from the student's class schedule.
        parking_times = self.get_parking_times()

        if parking_times is None:
            ui.notify("No classes found for today.", type="negative")
            return

        day, start_time, end_time = parking_times

        # Save the selected parking lot and times to the database.
        # If a plan already exists for today, update it instead.
        result = await run.io_bound(
            database.save_parking_plan,
            self.user_id,
            self.selected["lot"],
            day,
            start_time,
            end_time
        )

        # Stop if the database could not save the parking plan.
        if not result["success"]:
            ui.notify(result["message"], type="negative")
            return

        ui.notify(result["message"], type="positive")

        # Find the selected parking lot in our database.
        lot_name = self.selected["lot"]
        lots = database.get_all_lots()

        selected_lot = next(
            (lot for lot in lots if lot[1] == lot_name),
            None
        )

        if selected_lot is None:
            ui.notify("Parking lot not found.", type="negative")
            return

        # Find the building for the student's first class.
        building_name = self.selected["first_building"]
        buildings = load_buildings()

        selected_building = next(
            (building for building in buildings
             if building["name"] == building_name),
            None
        )

        if selected_building is None:
            ui.notify("Class building not found.", type="negative")
            return

        # Get the coordinates for the parking lot and classroom building.
        lot_coords = (selected_lot[2], selected_lot[3])
        building_coords = (
            selected_building["lat"],
            selected_building["lng"]
        )

        # Request the walking route without freezing the website.
        ui.notify("Loading walking route...", type="info")

        route = await run.io_bound(
            get_walking_route,
            lot_name,
            building_name,
            lot_coords,
            building_coords
        )

        if route is None:
            ui.notify("Could not load the walking route.", type="negative")
            return

        # Remove the previous route before drawing a new one.
        if self.route_line is not None:
            self.map_view.remove_layer(self.route_line)
            self.route_line = None

        # Convert the route coordinates into the order Leaflet expects.
        route_points = [
            (lat, lng)
            for lng, lat in route["coordinates"]
        ]

        # Draw the actual walking path on the campus map.
        self.route_line = self.map_view.generic_layer(
            name="polyline",
            args=[route_points, {"color": "blue", "weight": 5}]
        )

        # Move the map to the selected parking lot.
        self.map_view.set_center(lot_coords)

        # Show the estimated walking time and distance.
        minutes = route["duration_minutes"]
        distance = route["distance_meters"]

        ui.notify(
            f"Walking time: {minutes:.1f} minutes | "
            f"Distance: {distance:.0f} meters",
            type="positive",
            timeout=8000
        )

