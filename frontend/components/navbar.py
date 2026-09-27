from nicegui import ui


def navbar() -> None:
    """Render the shared site navigation."""
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
            on_click=lambda: ui.navigate.to('/register'),
        ).classes('yellow-button').props('unelevated')
