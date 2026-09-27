from nicegui import ui


from pathlib import Path

from nicegui import app

from frontend.styles.theme import install_theme


ASSETS_DIR = Path(__file__).parent / 'assets'

app.add_static_files('/assets', ASSETS_DIR)
install_theme()

# Importing page modules registers their NiceGUI routes.
from frontend.pages import home as _home
from frontend.pages import register as _register


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='Campus Route')
