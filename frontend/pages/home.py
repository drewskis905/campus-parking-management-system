from nicegui import ui

from frontend.components.navbar import navbar


@ui.page('/')
def home_page() -> None:
    """Render the Routely landing page."""
    navbar()

    with ui.column().classes(
        'home-hero w-full items-center text-center px-6 pt-24 pb-20'
    ):
        ui.label('ROUTE PLANNING, SIMPLIFIED').classes(
            'text-xs font-bold tracking-wide text-amber-600 border '
            'border-amber-400 rounded-full px-3 py-1'
        )
        ui.label('Plan your perfect\nroute in seconds').classes(
            'serif text-5xl md:text-7xl font-bold leading-tight '
            'whitespace-pre-line max-w-3xl mt-6'
        )
        ui.label(
            'Stress free campus routing perfect for new students.'
        ).classes('text-gray-600 text-base max-w-2xl leading-7 mt-5')

        with ui.row().classes('items-center gap-3 mt-7'):
            ui.button(
                '→  Get started.',
                on_click=lambda: ui.navigate.to('/register'),
            ).classes('yellow-button').props('unelevated')
            ui.button('See How It Works').classes(
                'outline-button bg-white/70'
            ).props('flat')

        with ui.column().classes('hero-card items-center justify-center mt-10'):
            ui.icon('explore').classes(
                'text-4xl text-amber-500 bg-amber-50 rounded-full p-4'
            )
            ui.label('Plan Your Route').classes(
                'serif text-xl font-bold mt-4'
            )
            ui.label('Map coming soon.').classes(
                'text-gray-400 text-sm mt-2'
            )
