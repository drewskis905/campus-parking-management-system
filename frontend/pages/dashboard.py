import sqlite3

from nicegui import app, run, ui

from database import database
from frontend.components.navbar import navbar


@ui.page('/dashboard')
async def dashboard_page() -> None:
    """Show the schedule belonging to the account in this browser's session."""
    user_id = app.storage.user.get('user_id')
    if type(user_id) is not int or user_id <= 0:
        ui.navigate.to('/')
        return

    navbar()
    with ui.column().classes('w-full max-w-6xl mx-auto px-4 py-8 md:px-8 gap-6'):
        ui.label('My Schedule').classes('serif text-3xl font-bold')

        try:
            schedule = await run.io_bound(database.get_user_schedule, user_id)
        except sqlite3.Error:
            ui.label('Your schedule could not be loaded. Please try again.').classes(
                'text-red-700'
            ).props('role=alert')
            return

        if not schedule:
            ui.label('You have no classes scheduled yet.').classes('text-gray-600')
            return

        rows = [
            {
                'id': class_id,
                'class_name': class_name,
                'building': building,
                'days': ', '.join(day.strip() for day in days.split('/')),
                'start_time': database.format_time(start_time),
                'end_time': database.format_time(end_time),
            }
            for class_id, _, class_name, building, days, start_time, end_time in schedule
        ]
        columns = [
            {'name': field, 'label': label, 'field': field, 'align': 'left'}
            for field, label in (
                ('class_name', 'Class'), ('building', 'Building'),
                ('days', 'Days'), ('start_time', 'Start time'), ('end_time', 'End time'),
            )
        ]
        ui.table(columns=columns, rows=rows, row_key='id').classes('w-full').props(
            'flat bordered wrap-cells'
        )
