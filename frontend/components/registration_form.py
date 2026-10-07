from nicegui import ui

from database import database
from frontend.components.class_schedule_row import class_schedule_row


def registration_form() -> None:
    """Render account fields and editable class rows without submitting data."""
    buildings = database.get_all('buildings', 'name') or []

    with ui.column().classes('w-full gap-6'):
        with ui.element('div').classes(
            'grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl mx-auto'
        ):
            ui.input(placeholder='First Name').props('outlined').classes(
                'w-full'
            )
            ui.input(placeholder='Last Name (Optional)').props(
                'outlined'
            ).classes('w-full')
            ui.input(placeholder='Email').props('outlined').classes(
                'w-full sm:col-span-2'
            )
            ui.input(placeholder='Password', password=True).props(
                'outlined'
            ).classes('w-full')
            ui.input(placeholder='Confirm Password', password=True).props(
                'outlined'
            ).classes('w-full')

        ui.separator()
        ui.label('Class Schedule').classes('serif text-2xl font-bold')

        with ui.column().classes('w-full gap-3') as class_rows:
            class_schedule_row(buildings)

        def add_class() -> None:
            with class_rows:
                class_schedule_row(buildings)

        ui.button('Add class', icon='add', on_click=add_class).props(
            'outline'
        )
        ui.button('Create account').classes('yellow-button self-end').props(
            'unelevated disable'
        )
