from dataclasses import dataclass

from nicegui import ui


WEEKDAYS = (
    ('Monday', 'M'),
    ('Tuesday', 'Tu'),
    ('Wednesday', 'W'),
    ('Thursday', 'Th'),
    ('Friday', 'F'),
    ('Saturday', 'Sa'),
)


def weekday_selector() -> set[str]:
    """Show toggle-style buttons that allow multiple selected days."""
    selected_days: set[str] = set()

    def add_day_button(day: str, short_name: str) -> None:
        button = ui.button(short_name).props('flat dense no-caps').classes(
            'weekday-button'
        ).tooltip(day)

        def toggle_day() -> None:
            if day in selected_days:
                selected_days.remove(day)
                button.classes(remove='weekday-button--selected')
            else:
                selected_days.add(day)
                button.classes(add='weekday-button--selected')

        button.on('click', toggle_day)

    with ui.row().classes('weekday-selector items-center'):
        for day, short_name in WEEKDAYS:
            add_day_button(day, short_name)
    return selected_days


@dataclass
class ClassScheduleFields:
    container: ui.element
    class_name: ui.input
    building: ui.select
    days: set[str]
    start_time: ui.time_input
    end_time: ui.time_input

    def values(self) -> dict[str, str]:
        return {
            'class_name': (self.class_name.value or '').strip(),
            'building': self.building.value or '',
            'day': '/'.join(day for day, _ in WEEKDAYS if day in self.days),
            'start_time': self.start_time.value or '',
            'end_time': self.end_time.value or '',
        }


def class_schedule_row(buildings: list[str]) -> ClassScheduleFields:
    """Render one removable class entry in the registration form."""
    with ui.element('div').classes('class-schedule-row') as row:
        class_name = ui.input('Class name').props('outlined').classes('w-full')
        building = ui.select(buildings, label='Building', with_input=True).props(
            'outlined'
        ).classes('w-full')

        with ui.column().classes('w-full gap-2'):
            ui.label('Class days').classes('text-sm text-gray-600')
            days = weekday_selector()

        start_time = ui.time_input('Start time').props('outlined').classes('w-full')
        end_time = ui.time_input('End time').props('outlined').classes('w-full')
        ui.button(icon='delete_outline', on_click=row.delete).props(
            'flat round'
        ).tooltip('Remove class')

    return ClassScheduleFields(row, class_name, building, days, start_time, end_time)
