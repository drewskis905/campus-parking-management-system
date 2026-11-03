import logging
from datetime import datetime

from nicegui import run, ui

from backend.algorithm_version2 import recommend_for_student


logger = logging.getLogger(__name__)


class ParkingRecommendations:
    """Display real recommendations; route updates and persistence are future work."""

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
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
            ui.label('This preview does not save your parking choice yet.').classes(
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
        """Stub: later draw lot → first class and last class → lot on the map."""

    def open_confirmation(self) -> None:
        if self.selected is None:
            return
        self.confirmation_text.set_text(f'Choose {self.selected["lot"]} for today’s parking?')
        self.dialog.open()

    def confirm_selection(self) -> None:
        """Stub: close the preview dialog without writing a parking plan."""
        self.dialog.close()
        ui.notify('Preview only. Your parking choice has not been saved.', type='info')
