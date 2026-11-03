import re
import sqlite3
from collections.abc import Callable

from nicegui import app, run, ui

from database import database
from frontend.components.registration_form import registration_form


def auth_dialog() -> Callable[[str], None]:
    """Create a login/register dialog and return a function to open either tab."""
    with ui.dialog() as dialog, ui.card().classes('auth-dialog-card p-6'):
        with ui.tabs().classes('w-full') as tabs:
            login_tab = ui.tab('Log In')
            register_tab = ui.tab('Register')

        with ui.tab_panels(tabs, value=login_tab).classes('w-full') as panels:
            with ui.tab_panel(login_tab):
                with ui.column().classes('w-full max-w-md mx-auto'):
                    login_email = ui.input('Email').props('type=email').classes('w-full')
                    login_password = ui.input('Password', password=True).classes('w-full')
                    login_error = ui.label().classes('text-red-700').props('role=alert')
                    login_status = ui.label().classes('text-green-700').props('role=status')

                    async def verify_login() -> None:
                        if not login_button.enabled:
                            return
                        login_error.set_text('')
                        login_status.set_text('')
                        email = (login_email.value or '').strip()
                        password = login_password.value or ''
                        if not email or not password.strip():
                            login_error.set_text('Please enter your email and password.')
                            return
                        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                            login_error.set_text('Please enter a valid email address.')
                            return
                        if len(password.encode('utf-8')) > 72:
                            login_error.set_text('Invalid email or password.')
                            return

                        login_button.disable()
                        try:
                            result = await run.io_bound(database.verify_password, email, password)
                            if not result['success']:
                                message = result['message']
                                login_error.set_text(
                                    message if message == 'Invalid email or password.'
                                    else 'Could not check login details. Please try again.'
                                )
                                return

                            user_id = await run.io_bound(database.get_user_id, email)
                            if user_id is None:
                                login_error.set_text('Could not find your account. Please try again.')
                                return
                            app.storage.user['user_id'] = user_id
                        except (sqlite3.Error, ValueError, OSError):
                            login_error.set_text('Could not check login details. Please try again.')
                            return
                        finally:
                            login_button.enable()

                        login_password.set_value('')
                        login_status.set_text('Signed in successfully.')
                        dialog.close()
                        ui.navigate.to('/dashboard')

                    login_button = ui.button('Log In', on_click=verify_login).classes(
                        'yellow-button w-full'
                    ).props('unelevated')
                    login_email.on('keydown.enter', verify_login)
                    login_password.on('keydown.enter', verify_login)

            with ui.tab_panel(register_tab):
                def registered(email: str) -> None:
                    login_email.set_value(email)
                    login_password.set_value('')
                    login_error.set_text('')
                    login_status.set_text('')
                    panels.set_value(login_tab)

                registration_form(on_registered=registered)

    def open_auth(tab: str = 'Log In') -> None:
        login_password.set_value('')
        login_error.set_text('')
        login_status.set_text('')
        panels.set_value(register_tab if tab == 'Register' else login_tab)
        dialog.open()

    return open_auth
