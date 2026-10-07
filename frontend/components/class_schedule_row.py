from nicegui import ui


WEEKDAYS = (
    ('Monday', 'M'),
    ('Tuesday', 'Tu'),
    ('Wednesday', 'W'),
    ('Thursday', 'Th'),
    ('Friday', 'F'),
    ('Saturday', 'Sa'),
)


def weekday_selector() -> None:
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


def class_schedule_row(buildings: list[str]) -> None:
    """Render one removable class entry in the registration form."""
    with ui.element('div').classes('class-schedule-row') as row:
        ui.input('Class name').props('outlined').classes('w-full')
        ui.select(buildings, label='Building', with_input=True).props(
            'outlined'
        ).classes('w-full')

        with ui.column().classes('w-full gap-2'):
            ui.label('Class days').classes('text-sm text-gray-600')
            weekday_selector()

        ui.time_input('Start time').props('outlined').classes('w-full')
        ui.time_input('End time').props('outlined').classes('w-full')
        ui.button(icon='delete_outline', on_click=row.delete).props(
            'flat round'
        ).tooltip('Remove class')
