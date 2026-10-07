from nicegui import ui


GLOBAL_CSS = '''
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

    body {
        margin: 0;
        background: #fcfcfa;
        color: #1d1d1b;
        font-family: 'DM Sans', sans-serif;
    }

    .site-header {
        position: relative;
        z-index: 10;
        background: rgba(255, 255, 255, 0.84);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    .home-hero {
        position: relative;
        isolation: isolate;
        min-height: calc(100vh - 73px);
        overflow: hidden;
    }

    .home-hero::before {
        content: '';
        position: absolute;
        inset: 0;
        z-index: -2;
        background-image: url('/assets/beach-hero.png');
        background-size: cover;
        background-position: center;
    }

    .home-hero::after {
        content: '';
        position: absolute;
        inset: 0;
        z-index: -1;
        background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.32) 0%,
            rgba(255, 250, 235, 0.52) 58%,
            rgba(252, 252, 250, 0.80) 100%
        );
    }

    .serif {
        font-family: 'Playfair Display', Georgia, serif;
    }

    .nav-link {
        color: #555550;
        font-size: 14px;
        text-decoration: none;
    }

    .nav-link:hover {
        color: #f5a900;
    }

    .yellow-button {
        background: #ffad00;
        color: #1d1d1b;
        border-radius: 999px;
        font-weight: 700;
        padding: 12px 22px;
    }

    .outline-button {
        border: 1px solid #d7d7d2;
        color: #4f4f4a;
        border-radius: 999px;
        font-weight: 600;
        padding: 11px 22px;
    }

    .hero-card {
        width: min(720px, 90vw);
        height: 220px;
        border: 1px solid rgba(238, 238, 234, 0.85);
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.90);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        box-shadow: 0 18px 40px rgba(40, 40, 30, 0.10);
    }

    .auth-dialog-card {
        width: min(1100px, 96vw);
        max-width: none;
        max-height: 90vh;
        overflow-y: auto;
    }

    .class-schedule-row {
        display: grid;
        grid-template-columns: minmax(130px, 1.2fr) minmax(140px, 1.1fr)
            minmax(235px, 1.5fr) minmax(115px, 1fr)
            minmax(115px, 1fr) auto;
        gap: 12px;
        align-items: end;
        width: 100%;
        padding: 16px;
        border: 1px solid #e6e6df;
        border-radius: 16px;
    }

    .weekday-selector {
        display: inline-flex;
        flex-wrap: nowrap;
        gap: 0;
        width: max-content;
        max-width: 100%;
        overflow: hidden;
        border-radius: 4px;
        border: 1px solid #d7d7d2;
        background: white;
    }

    .weekday-selector .weekday-button {
        min-width: 36px;
        min-height: 36px;
        padding: 0 7px;
        border-radius: 0;
        background: white;
        color: #1d1d1b;
    }

    .weekday-selector .weekday-button + .weekday-button {
        border-left: 1px solid #d7d7d2;
    }

    .weekday-selector .weekday-button--selected {
        background: #ffad00;
        color: #1d1d1b;
    }

    .weekday-selector .weekday-button:focus-visible {
        outline: 2px solid #1d1d1b;
        outline-offset: -2px;
    }

    @media (max-width: 1000px) {
        .class-schedule-row {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 600px) {
        .class-schedule-row {
            grid-template-columns: minmax(0, 1fr);
        }
    }

    @media (max-width: 700px) {
        .nav-links {
            display: none;
        }

        .home-hero::before {
            background-position: 58% center;
        }
    }
'''


def install_theme() -> None:
    """Install styles shared by every frontend page."""
    ui.add_css(GLOBAL_CSS, shared=True)
