import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, call, patch

from nicegui import app, ui

from database import database
from frontend.components.auth_dialog import auth_dialog


class LoginTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_patch = patch.object(database, 'DATABASE', str(Path(temp_dir.name) / 'login.db'))
        db_patch.start()
        self.addCleanup(db_patch.stop)
        database.create_tables()
        self.password_value = ' Test password! '
        database.add_user('Test', 'Student', 'student@example.com', self.password_value)

        self.session = {}
        storage_patch = patch.object(type(app.storage), 'user', new_callable=PropertyMock,
                                     return_value=self.session)
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        navigation_patch = patch.object(ui.navigate, 'to')
        self.navigate = navigation_patch.start()
        self.addCleanup(navigation_patch.stop)

        original_button = ui.button

        def create_button(*args, **kwargs):
            button = original_button(*args, **kwargs)
            if args and args[0] == 'Log In':
                self.verify_login = kwargs['on_click']
                self.button = button
            return button

        async def execute(function, *args):
            self.assertFalse(self.button.enabled)
            return function(*args)

        io_patch = patch('frontend.components.auth_dialog.run.io_bound', side_effect=execute)
        self.io_bound = io_patch.start()
        self.addCleanup(io_patch.stop)
        existing_ids = set(ui.context.client.elements)
        with patch.object(ui, 'button', side_effect=create_button):
            with ui.column() as self.root:
                self.open_dialog = auth_dialog()
        elements = [e for e in self.root.client.elements.values() if e.id not in existing_ids]

        def cleanup_elements():
            for element in elements:
                if not element.is_deleted:
                    element.delete()

        self.addCleanup(cleanup_elements)
        self.email = next(e for e in elements if isinstance(e, ui.input) and e.label == 'Email')
        self.password = next(e for e in elements if isinstance(e, ui.input) and e.label == 'Password')
        self.error = next(e for e in elements if e._props.get('role') == 'alert')
        self.status = next(e for e in elements if e._props.get('role') == 'status')

    def submit(self, email='student@example.com', password=None):
        self.email.set_value(email)
        self.password.set_value(self.password_value if password is None else password)

        async def run_submit():
            with self.root:
                await self.verify_login()

        asyncio.run(run_submit())

    def test_missing_fields_do_not_call_backend(self):
        for email, password in (('', ''), ('student@example.com', ''), ('', 'Password!')):
            with self.subTest(email=email):
                self.submit(email, password)
                self.assertEqual(self.error.text, 'Please enter your email and password.')
        self.io_bound.assert_not_called()

    def test_invalid_email_does_not_call_backend(self):
        self.submit('invalid-email')
        self.assertEqual(self.error.text, 'Please enter a valid email address.')
        self.io_bound.assert_not_called()

    def test_wrong_password_and_unknown_email_have_same_message(self):
        self.submit(password='wrong')
        self.assertEqual(self.error.text, 'Invalid email or password.')
        self.submit('unknown@example.com')
        self.assertEqual(self.error.text, 'Invalid email or password.')
        self.assertEqual(self.status.text, '')
        self.assertEqual(self.session, {})
        self.navigate.assert_not_called()
        self.assertTrue(self.button.enabled)

    def test_success_trims_email_preserves_password_and_clears_it(self):
        self.submit(' student@example.com ')
        self.assertEqual(self.error.text, '')
        self.assertEqual(self.status.text, 'Signed in successfully.')
        self.assertEqual(self.password.value, '')
        self.assertTrue(self.button.enabled)
        self.io_bound.assert_has_awaits([
            call(database.verify_password, 'student@example.com', self.password_value),
            call(database.get_user_id, 'student@example.com'),
        ])
        self.assertEqual(self.session, {'user_id': database.get_user_id('student@example.com')})
        self.navigate.assert_called_once_with('/dashboard')

    def test_missing_account_does_not_create_a_session(self):
        self.io_bound.side_effect = [{'success': True}, None]
        self.submit()
        self.assertEqual(self.session, {})
        self.assertEqual(self.error.text, 'Could not find your account. Please try again.')
        self.assertTrue(self.button.enabled)

    def test_failed_login_does_not_replace_an_existing_identity(self):
        self.session['user_id'] = 123
        self.submit(password='wrong')
        self.assertEqual(self.session, {'user_id': 123})

    def test_oversized_password_does_not_raise_bcrypt_error(self):
        self.submit(password='x' * 73)
        self.assertEqual(self.error.text, 'Invalid email or password.')
        self.io_bound.assert_not_called()

    def test_database_exception_shows_error_and_reenables_button(self):
        self.io_bound.side_effect = sqlite3.OperationalError('private database path')
        self.submit()
        self.assertEqual(self.error.text, 'Could not check login details. Please try again.')
        self.assertTrue(self.button.enabled)

    def test_database_error_result_does_not_expose_internal_message(self):
        self.io_bound.side_effect = None
        self.io_bound.return_value = {'success': False, 'message': 'Database error: private details'}
        self.submit()
        self.assertEqual(self.error.text, 'Could not check login details. Please try again.')

    def test_reopening_clears_old_feedback_and_password(self):
        self.submit()
        self.password.set_value('Unsubmitted password')
        with self.root:
            self.open_dialog()
        self.assertEqual(self.status.text, '')
        self.assertEqual(self.password.value, '')


if __name__ == '__main__':
    unittest.main()
