from nicegui import ui


from frontend.components.navbar import navbar


@ui.page('/register')
def register_page():
    navbar()

    with ui.card().classes('w-full max-w-md mx-auto mt-16 p-8'):
        ui.label('Create Account')

        username = ui.input('Username')
        email = ui.input('Email')
        password = ui.input(
            'Password',
            password=True,
            password_toggle_button=True
        )

        ui.button(
            'Register',
            on_click=lambda: ui.notify(
                f'Creating account for {username.value}'
            )
        )
