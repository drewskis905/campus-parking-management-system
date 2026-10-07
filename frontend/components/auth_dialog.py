from collections.abc import Callable

from nicegui import ui

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
                    ui.input('Email').classes('w-full')
                    ui.input('Password', password=True).classes('w-full')

            with ui.tab_panel(register_tab):
                registration_form()

    def open_auth(tab: str = 'Log In') -> None:
        panels.set_value(register_tab if tab == 'Register' else login_tab)
        dialog.open()

    return open_auth
