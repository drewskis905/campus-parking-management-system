
import re
import sqlite3
import bcrypt
from nicegui import app, run, ui
from datetime import datetime
from database import database
from frontend.components.navbar import navbar, logout


# Get the student's account information from the database.
def load_settings(user_id):
    with database.get_connection() as conn:
        user = conn.execute(
            "SELECT first_name, last_name, email FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

    return user


@ui.page('/settings')
async def settings_page():

    # Make sure the student is logged in before showing their settings.
    user_id = app.storage.user.get('user_id')

    if type(user_id) is not int or user_id <= 0:
        ui.navigate.to('/')
        return

    # Load the student's account information.
    try:
        user = await run.io_bound(load_settings, user_id)
    except sqlite3.Error:
        ui.label('Could not load settings. Please try again.')
        return

    if user is None:
        ui.navigate.to('/')
        return

    navbar()

    with ui.column().classes(
        'w-full max-w-3xl mx-auto px-4 py-8 gap-6'
    ):

        ui.label('Settings').classes('serif text-4xl font-bold')
        ui.label(
            'Manage your account and class schedule.'
        ).classes('text-gray-600')

        # Let students update their name and email address.
        with ui.card().classes('w-full p-6 rounded-2xl gap-4'):
            ui.label('Profile Settings').classes(
                'serif text-2xl font-bold'
            )

            first_name = ui.input(
                'First Name', value=user[0]
            ).classes('w-full')

            last_name = ui.input(
                'Last Name', value=user[1]
            ).classes('w-full')

            email = ui.input(
                'Email', value=user[2]
            ).classes('w-full')

            async def save_profile():
                first = (first_name.value or '').strip()
                last = (last_name.value or '').strip()
                address = (email.value or '').strip()

                # Check the information before saving it to the database.
                if not first or not last or not re.fullmatch(
                    r'[^\s@]+@[^\s@]+\.[^\s@]+', address
                ):
                    ui.notify(
                        'Please enter a valid name and email.',
                        type='negative'
                    )
                    return

                def update_profile():
                    with database.get_connection() as conn:
                        conn.execute(
                            """UPDATE users
                               SET first_name = ?, last_name = ?, email = ?
                               WHERE id = ?""",
                            (first, last, address, user_id)
                        )

                try:
                    await run.io_bound(update_profile)
                    ui.notify('Profile updated!', type='positive')
                except sqlite3.IntegrityError:
                    ui.notify(
                        'That email is already in use.',
                        type='negative'
                    )
                except sqlite3.Error:
                    ui.notify(
                        'Could not update profile.',
                        type='negative'
                    )

            ui.button(
                'Save Profile', on_click=save_profile
            ).classes('yellow-button')

        # Let students change their password after checking the old one.
        with ui.card().classes('w-full p-6 rounded-2xl gap-4'):
            ui.label('Change Password').classes(
                'serif text-2xl font-bold'
            )

            current_password = ui.input(
                'Current Password',
                password=True,
                password_toggle_button=True
            ).classes('w-full')

            new_password = ui.input(
                'New Password',
                password=True,
                password_toggle_button=True
            ).classes('w-full')

            confirm_password = ui.input(
                'Confirm New Password',
                password=True,
                password_toggle_button=True
            ).classes('w-full')

            async def change_password():
                current = current_password.value or ''
                new = new_password.value or ''
                confirm = confirm_password.value or ''

                # Check the new password before trying to update it.
                if len(new) < 8:
                    ui.notify(
                        'Password must have at least 8 characters.',
                        type='negative'
                    )
                    return

                if len(new.encode('utf-8')) > 72:
                    ui.notify(
                        'Password is too long.',
                        type='negative'
                    )
                    return

                if new != confirm:
                    ui.notify(
                        'New passwords do not match.',
                        type='negative'
                    )
                    return

                def update_password():
                    with database.get_connection() as conn:
                        row = conn.execute(
                            "SELECT password_hash FROM users WHERE id = ?",
                            (user_id,)
                        ).fetchone()

                        # Verify the current password before replacing it.
                        if row is None or not bcrypt.checkpw(
                            current.encode('utf-8'),
                            row[0].encode('utf-8')
                        ):
                            return False

                        # Hash the new password so we never store plain text.
                        hashed = bcrypt.hashpw(
                            new.encode('utf-8'),
                            bcrypt.gensalt()
                        ).decode('utf-8')

                        conn.execute(
                            "UPDATE users SET password_hash = ? WHERE id = ?",
                            (hashed, user_id)
                        )

                    return True

                try:
                    success = await run.io_bound(update_password)

                    if success:
                        current_password.value = ''
                        new_password.value = ''
                        confirm_password.value = ''

                        ui.notify(
                            'Password changed successfully!',
                            type='positive'
                        )
                    else:
                        ui.notify(
                            'Current password is incorrect.',
                            type='negative'
                        )
                except (sqlite3.Error, ValueError):
                    ui.notify(
                        'Could not change password.',
                        type='negative'
                    )

            ui.button(
                'Change Password', on_click=change_password
            ).classes('yellow-button')

        # Let students manage their classes without going back to registration.
        with ui.card().classes(
                'w-full p-6 rounded-2xl gap-4'
        ).props('id=class-schedule'):
            ui.label('Class Schedule').classes('serif text-2xl font-bold')
            ui.label(
                'Add, edit, or remove classes from your schedule.'
            ).classes('text-gray-600')

            schedule_list = ui.column().classes('w-full gap-3')

            days = [
                'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday'
            ]

            # Load building names from the existing database.
            buildings = await run.io_bound(database.get_all_buildings)
            building_names = sorted(building[1] for building in buildings)

            def open_class_form(existing=None):
                editing = existing is not None

                with ui.dialog() as dialog, ui.card().classes(
                        'w-full max-w-lg p-6 gap-4'
                ):
                    ui.label(
                        'Edit Class' if editing else 'Add Class'
                    ).classes('text-2xl font-bold')

                    class_name = ui.input(
                        'Class Name',
                        value=existing[2] if editing else ''
                    ).classes('w-full')

                    building = ui.select(
                        building_names,
                        label='Building',
                        value=existing[3] if editing else None
                    ).classes('w-full').props('outlined')

                    # Allow multiple days for classes that meet more than once.
                    selected_days = ui.select(
                        days,
                        label='Class Days',
                        multiple=True,
                        value=existing[4].split('/') if editing else []
                    ).classes('w-full').props('outlined use-chips')

                    ui.label('Use 24-hour time (example: 13:30 = 1:30 PM)').classes(
                        'text-sm text-gray-600'
                    )

                    start_time = ui.input(
                        'Start Time (HH:MM)',
                        value=existing[5] if editing else ''
                    ).classes('w-full')

                    end_time = ui.input(
                        'End Time (HH:MM)',
                        value=existing[6] if editing else ''
                    ).classes('w-full')

                    async def save_class():
                        name = (class_name.value or '').strip()
                        chosen_building = building.value
                        chosen_days = selected_days.value or []
                        start = (start_time.value or '').strip()
                        end = (end_time.value or '').strip()

                        # Make sure the student entered all required information.
                        if not all([
                            name, chosen_building, chosen_days, start, end
                        ]):
                            ui.notify(
                                'Please fill in all fields.',
                                type='negative'
                            )
                            return

                        # Check the time format before sending it to the database.
                        try:
                            datetime.strptime(start, '%H:%M')
                            datetime.strptime(end, '%H:%M')
                        except ValueError:
                            ui.notify(
                                'Enter times as HH:MM, like 09:30 or 14:00.',
                                type='negative'
                            )
                            return

                        day_string = '/'.join(chosen_days)

                        if editing:
                            result = await run.io_bound(
                                database.update_schedule,
                                user_id, existing[0], name, chosen_building,
                                day_string, start, end
                            )
                        else:
                            result = await run.io_bound(
                                database.add_schedule,
                                user_id, name, chosen_building,
                                day_string, start, end
                            )

                        if result['success']:
                            ui.notify(result['message'], type='positive')
                            dialog.close()
                            await refresh_schedule()
                        else:
                            ui.notify(result['message'], type='negative')

                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button('Cancel', on_click=dialog.close).props(
                            'flat'
                        )
                        ui.button(
                            'Save Class', on_click=save_class
                        ).classes('yellow-button')

                dialog.open()

            def confirm_delete(schedule):
                with ui.dialog() as dialog, ui.card().classes('p-6 gap-4'):
                    ui.label('Delete Class?').classes('text-xl font-bold')
                    ui.label(
                        f'Are you sure you want to remove {schedule[2]}?'
                    )

                    async def remove_class():
                        result = await run.io_bound(
                            database.delete_schedule,
                            user_id, schedule[0]
                        )

                        if result['success']:
                            dialog.close()
                            ui.notify(result['message'], type='positive')
                            await refresh_schedule()
                        else:
                            ui.notify(result['message'], type='negative')

                    with ui.row().classes('justify-end gap-2'):
                        ui.button('Cancel', on_click=dialog.close).props(
                            'flat'
                        )
                        ui.button(
                            'Delete', on_click=remove_class
                        ).props('color=negative')

                dialog.open()

            async def refresh_schedule():
                # Reload classes so the page shows changes right after saving.
                current_schedule = await run.io_bound(
                    database.get_user_schedule, user_id
                )

                schedule_list.clear()

                with schedule_list:
                    if not current_schedule:
                        ui.label('No classes added yet.').classes(
                            'text-gray-600'
                        )

                    for schedule in current_schedule:
                        with ui.card().classes(
                                'w-full p-4 rounded-xl'
                        ):
                            ui.label(schedule[2]).classes(
                                'font-bold text-lg'
                            )
                            ui.label(f'Building: {schedule[3]}')
                            ui.label(
                                f'Days: {schedule[4].replace("/", ", ")}'
                            )
                            ui.label(
                                f'Time: {database.format_time(schedule[5])}'
                                f' - {database.format_time(schedule[6])}'
                            )

                            with ui.row().classes('gap-2'):
                                ui.button(
                                    'Edit',
                                    on_click=lambda s=schedule: open_class_form(s)
                                ).props('outline')

                                ui.button(
                                    'Delete',
                                    on_click=lambda s=schedule: confirm_delete(s)
                                ).props('flat color=negative')
            ui.button(
                'Add Class',
                on_click=lambda: open_class_form()
            ).classes('yellow-button')

            await refresh_schedule()

        # Let students confirm before permanently deleting their account.
        def open_delete_account():
            with ui.dialog() as dialog, ui.card().classes(
                    'w-full max-w-lg p-6 gap-4'
            ):
                ui.label('Delete Your Account?').classes(
                    'serif text-2xl font-bold text-red-600'
                )

                ui.label(
                    'Are you sure you want to permanently delete '
                    'your Campus Route account?'
                )

                ui.label('All your saved information will be deleted, including:')

                ui.label('• Personal account information')
                ui.label('• Class schedules')
                ui.label('• Parking plans')
                ui.label('• Parking preferences')

                ui.label(
                    'This action is permanent and cannot be undone.'
                ).classes('text-red-600 font-bold')

                # Require the current password to confirm account deletion.
                password = ui.input(
                    'Enter your password to confirm',
                    password=True,
                    password_toggle_button=True
                ).classes('w-full').props('outlined')

                async def confirm_delete_account():
                    # Make sure the student entered their password.
                    if not password.value:
                        ui.notify(
                            'Please enter your password.',
                            type='negative'
                        )
                        return

                    # Make sure the student is still signed in.
                    if app.storage.user.get('user_id') != user_id:
                        logout()
                        return

                    delete_button.disable()

                    # Verify the password and delete the account.
                    try:
                        result = await run.io_bound(
                            database.delete_account,
                            user_id,
                            password.value
                        )

                        if not result['success']:
                            ui.notify(result['message'], type='negative')
                            return

                        ui.notify(result['message'], type='positive')
                        dialog.close()

                        # Log the student out after deleting their account.
                        logout()

                    finally:
                        delete_button.enable()

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button(
                        'Cancel', on_click=dialog.close
                    ).props('flat no-caps')

                    delete_button = ui.button(
                        'Delete Account',
                        on_click=confirm_delete_account
                    ).props('color=negative no-caps unelevated')

            dialog.open()

        # Give students the option to log out or delete their account.
        with ui.card().classes('w-full p-6 rounded-2xl gap-3'):
            ui.label('Account').classes('serif text-2xl font-bold')

            with ui.row().classes('w-full items-center gap-3'):
                ui.button(
                    'Logout', on_click=logout
                ).classes('outline-button')

                ui.button(
                    'Delete Account',
                    icon='delete_outline',
                    on_click=open_delete_account
                ).props('outline color=negative no-caps')
