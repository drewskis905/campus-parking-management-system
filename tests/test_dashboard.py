import asyncio
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, patch

from nicegui import app, ui

from database import database
from frontend.components.navbar import logout
from frontend.pages.dashboard import dashboard_page


class DashboardTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        db_patch = patch.object(database, 'DATABASE', str(Path(directory.name) / 'dashboard.db'))
        db_patch.start()
        self.addCleanup(db_patch.stop)
        database.create_tables()
        self.first_id = database.add_user('First', 'Student', 'first@example.com', 'Password!')['user_id']
        self.second_id = database.add_user('Second', 'Student', 'second@example.com', 'Password!')['user_id']
        database.add_schedule(self.first_id, 'CECS 101', 'Engineering', 'Monday/Wednesday', '09:00', '10:00')
        database.add_schedule(self.second_id, 'MATH 101', 'Science', 'Tuesday', '13:00', '14:00')

        self.session = {}
        session_patch = patch.object(type(app.storage), 'user', new_callable=PropertyMock,
                                    return_value=self.session)
        session_patch.start()
        self.addCleanup(session_patch.stop)
        navigate_patch = patch.object(ui.navigate, 'to')
        self.navigate = navigate_patch.start()
        self.addCleanup(navigate_patch.stop)

        async def execute(function, *args):
            return function(*args)

        io_patch = patch('frontend.pages.dashboard.run.io_bound', side_effect=execute)
        self.io_bound = io_patch.start()
        self.addCleanup(io_patch.stop)

    def render(self):
        with ui.column() as root:
            pass
        self.addCleanup(root.delete)

        async def build():
            with root:
                await dashboard_page()

        asyncio.run(build())
        return root

    def test_signed_out_visitor_does_not_load_any_schedule(self):
        self.render()
        self.navigate.assert_called_once_with('/')
        self.io_bound.assert_not_called()

    def test_malformed_session_does_not_load_schedule(self):
        self.session['user_id'] = '1 OR 1=1'
        self.render()
        self.navigate.assert_called_once_with('/')
        self.io_bound.assert_not_called()

    def test_each_account_only_sees_its_own_classes(self):
        for user_id, expected_class in ((self.first_id, 'CECS 101'), (self.second_id, 'MATH 101')):
            with self.subTest(user_id=user_id):
                self.session['user_id'] = user_id
                root = self.render()
                table = next(e for e in root.descendants() if isinstance(e, ui.table))
                self.assertEqual([row['class_name'] for row in table.rows], [expected_class])
                self.io_bound.assert_awaited_with(database.get_user_schedule, user_id)
                if user_id == self.first_id:
                    self.assertEqual(table.rows[0]['days'], 'Monday, Wednesday')
                    self.assertEqual(table.rows[0]['start_time'], '9:00 AM')
                    self.assertEqual(table.rows[0]['end_time'], '10:00 AM')
        self.navigate.assert_not_called()

    def test_empty_schedule_has_clear_message(self):
        database.delete_user_schedule(self.first_id)
        self.session['user_id'] = self.first_id
        root = self.render()
        self.assertTrue(any(getattr(e, 'text', '') == 'You have no classes scheduled yet.'
                            for e in root.descendants()))

    def test_logout_blocks_dashboard_on_next_visit(self):
        self.session['user_id'] = self.first_id
        root = self.render()
        self.assertTrue(any(isinstance(e, ui.button) and e.text == 'Logout'
                            for e in root.descendants()))
        with root:
            logout()
        self.io_bound.reset_mock()
        self.render()
        self.navigate.assert_called_with('/')
        self.io_bound.assert_not_called()

    def test_database_failure_shows_error_without_private_details(self):
        self.session['user_id'] = self.first_id
        self.io_bound.side_effect = sqlite3.OperationalError('private database path')
        root = self.render()
        error = next(e for e in root.descendants() if e._props.get('role') == 'alert')
        self.assertEqual(error.text, 'Your schedule could not be loaded. Please try again.')


if __name__ == '__main__':
    unittest.main()
