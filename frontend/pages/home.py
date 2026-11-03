from nicegui import ui

from frontend.components.navbar import navbar

from database import database

@ui.page('/')
def home_page() -> None:
    """Render the landing page."""
    open_auth = navbar()

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
                on_click=lambda: open_auth('Register'),
            ).classes('yellow-button').props('unelevated')
            ui.button('See How It Works').classes(
                'outline-button bg-white/70'
            ).props('flat')

        with ui.column().classes('hero-card items-center justify-center mt-10'):
            options = {
                'zoomControl': False,
                'scrollWheelZoom': False,
                'doubleClickZoom': False,
                'boxZoom': False,
                'keyboard': False,
                'dragging': False,
            }
            CSULB_LAT = 33.782
            CSULB_LNG = -118.112
            m = ui.leaflet(center=(CSULB_LAT, CSULB_LNG), zoom=14, options=options)