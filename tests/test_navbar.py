import unittest
from unittest.mock import PropertyMock, patch

from nicegui import app, ui

from frontend.components.navbar import logout, navbar


class NavbarTests(unittest.TestCase):
    def setUp(self):
        self.session = {}
        storage_patch = patch.object(type(app.storage), 'user', new_callable=PropertyMock,
                                     return_value=self.session)
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        navigation_patch = patch.object(ui.navigate, 'to')
        self.navigate = navigation_patch.start()
        self.addCleanup(navigation_patch.stop)
        dialog_patch = patch('frontend.components.navbar.auth_dialog')
        self.auth_dialog = dialog_patch.start()
        self.addCleanup(dialog_patch.stop)

    def render(self):
        with ui.column() as root:
            open_auth = navbar()
        self.addCleanup(root.delete)
        return root, open_auth

    def button_labels(self, root):
        return [e.text for e in root.descendants() if isinstance(e, ui.button)]

    def test_signed_out_navbar_shows_login_button(self):
        root, open_auth = self.render()
        self.assertIn('Log In / Register', self.button_labels(root))
        self.assertNotIn('Logout', self.button_labels(root))
        self.assertIs(open_auth, self.auth_dialog.return_value)

    def test_signed_in_navbar_has_dashboard_and_logout(self):
        self.session['user_id'] = 11
        root, _ = self.render()
        self.assertIn('Logout', self.button_labels(root))
        self.assertNotIn('Log In / Register', self.button_labels(root))
        self.assertTrue(any(isinstance(e, ui.link) and e._props.get('href') == '/dashboard'
                            for e in root.descendants()))
        self.auth_dialog.assert_not_called()

    def test_signed_in_home_call_to_action_opens_dashboard(self):
        self.session['user_id'] = 11
        _, open_auth = self.render()
        open_auth('Register')
        self.navigate.assert_called_once_with('/dashboard')

    def test_logout_clears_identity_and_restores_login_controls_on_reload(self):
        self.session.update(user_id=11, unrelated_preference='value')
        logout()
        self.assertEqual(self.session, {'unrelated_preference': 'value'})
        self.navigate.assert_called_once_with('/')
        root, _ = self.render()
        self.assertIn('Log In / Register', self.button_labels(root))
        self.assertNotIn('Logout', self.button_labels(root))


if __name__ == '__main__':
    unittest.main()
