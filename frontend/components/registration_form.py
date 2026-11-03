import re
from collections.abc import Callable

from nicegui import run, ui

from database import database
from frontend.components.class_schedule_row import class_schedule_row


def registration_form(on_registered: Callable[[str], None] | None = None) -> None:
    """Create an account and its class schedule from the registration form."""
    buildings = database.get_all('buildings', 'name') or []

    with ui.column().classes('w-full gap-6'):
        with ui.element('div').classes(
            'grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl mx-auto'
        ):
            first_name = ui.input(placeholder='First Name').props('outlined').classes(
                'w-full'
            )
            last_name = ui.input(placeholder='Last Name').props(
                'outlined'
            ).classes('w-full')
            email = ui.input(placeholder='Email').props('outlined type=email').classes(
                'w-full sm:col-span-2'
            )
            password = ui.input(placeholder='Password', password=True).props(
                'outlined'
            ).classes('w-full')
            confirm_password = ui.input(placeholder='Confirm Password', password=True).props(
                'outlined'
            ).classes('w-full')

        ui.separator()
        ui.label('Class Schedule').classes('serif text-2xl font-bold')

        with ui.column().classes('w-full gap-3') as class_rows:
            rows = [class_schedule_row(buildings)]

        def add_class() -> None:
            with class_rows:
                rows[:] = [row for row in rows if not row.container.is_deleted]
                rows.append(class_schedule_row(buildings))

        error_message = ui.label().classes('text-red-700').props('role=alert')

        async def submit() -> None:
            error_message.set_text('')
            account_email = (email.value or '').strip()
            if not all((field.value or '').strip() for field in
                       (first_name, last_name, email, password, confirm_password)):
                error_message.set_text('Please complete all account fields, including Last Name.')
                return
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', account_email):
                error_message.set_text('Please enter a valid email address.')
                return
            if password.value != confirm_password.value:
                error_message.set_text('The passwords do not match.')
                return
            if len(password.value.encode('utf-8')) > 72:
                error_message.set_text('Your password is too long; use at most 72 UTF-8 bytes.')
                return

            schedules = [row.values() for row in rows if not row.container.is_deleted]
            for index, schedule in enumerate(schedules, start=1):
                if not all(schedule.values()):
                    error_message.set_text(f'Class {index}: complete all fields and select at least one day, or remove this class.')
                    return
                if not database.validate_time(schedule['start_time'], schedule['end_time']):
                    error_message.set_text(f'Class {index}: end time must follow start time, between 07:00 and 23:00.')
                    return

            submit_button.disable()
            try:
                result = await run.io_bound(
                    database.register_user, first_name.value.strip(),
                    last_name.value.strip(), account_email, password.value, schedules,
                )
            finally:
                submit_button.enable()
            if not result['success']:
                error_message.set_text(result['message'])
                return

            for field in (first_name, last_name, email, password, confirm_password):
                field.set_value('')
            class_rows.clear()
            rows.clear()
            add_class()
            ui.notify('Your account and class schedule have been created.', type='positive')
            if on_registered is not None:
                on_registered(account_email)

        ui.button('Add class', icon='add', on_click=add_class).props(
            'outline'
        )
        submit_button = ui.button('Create account', on_click=submit).classes('yellow-button self-end').props(
            'unelevated'
        )
