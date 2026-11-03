from nicegui import ui

from frontend.config import CAMPUS_MAP_SETTINGS, CampusMapSettings


def campus_map(
    settings: CampusMapSettings = CAMPUS_MAP_SETTINGS,
    *,
    interactive: bool = False,
    height: int = 220,
) -> ui.leaflet:
    """Create an independent map using the shared campus configuration."""
    options = {
        control: interactive
        for control in (
            'zoomControl', 'scrollWheelZoom', 'doubleClickZoom',
            'boxZoom', 'keyboard', 'dragging', 'touchZoom',
        )
    }
    return ui.leaflet(
        center=(settings.latitude, settings.longitude),
        zoom=settings.zoom,
        options=options,
    ).classes('w-full').style(f'height: {height}px')
