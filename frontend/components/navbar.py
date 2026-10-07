from collections.abc import Callable

from nicegui import ui

from frontend.components.auth_dialog import auth_dialog


def navbar() -> Callable[[str], None]:
    """Render the shared site navigation."""
    open_auth = auth_dialog()
    with ui.row().classes(
        'site-header w-full items-center justify-between px-4 md:px-8 py-4 '
        'border-b border-gray-100'
    ):
        with ui.row().classes('items-center gap-3'):
            ui.icon('explore', color='#ffad00').classes('text-3xl')
            ui.label('Campus Route').classes('serif text-xl font-bold')

        with ui.row().classes('nav-links items-center gap-8'):
            ui.link('Features', '/#features').classes('nav-link')
            ui.link('How It Works', '/#how-it-works').classes('nav-link')
            ui.link('Example', '/#example').classes('nav-link')

        ui.button(
            'Log In / Register',
            on_click=lambda: open_auth('Log In'),
        ).classes('yellow-button').props('unelevated')

    return open_auth
