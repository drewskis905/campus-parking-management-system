import asyncio
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from database import database


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        database_path = str(Path(self.temp_dir.name) / 'registration.db')
        self.db_patch = patch.object(database, 'DATABASE', database_path)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        database.create_tables()
        database.add_building('Engineering', 33.78, -118.11)

    def schedule(self, **changes):
        return {
            'class_name': 'CECS 101', 'building': 'Engineering',
            'day': 'Monday/Wednesday', 'start_time': '09:00',
            'end_time': '10:00', **changes,
        }

    def register(self, schedules, email='student@example.com', last_name='Student'):
        return database.register_user('Test', last_name, email, 'Test password!', schedules)

    def assert_no_registration(self):
        with closing(database.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM schedules').fetchone()[0], 0)

    def test_saves_account_classes_and_verifiable_password(self):
        result = self.register([
            self.schedule(),
            self.schedule(class_name='MATH 101', start_time='10:00', end_time='11:00'),
        ])
        self.assertTrue(result['success'], result)
        self.assertEqual(database.get_user_id('student@example.com'), result['user_id'])
        self.assertEqual(len(database.get_user_schedule(result['user_id'])), 2)
        self.assertTrue(database.verify_password('student@example.com', 'Test password!')['success'])
        self.assertFalse(database.verify_password('student@example.com', 'wrong')['success'])

    def test_duplicate_email_does_not_change_existing_account(self):
        original = self.register([self.schedule()])
        duplicate = self.register([])
        self.assertFalse(duplicate['success'])
        self.assertIn('already exists', duplicate['message'])
        self.assertEqual(len(database.get_user_schedule(original['user_id'])), 1)
        with closing(database.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0], 1)

    def test_invalid_later_class_rolls_back_account_and_previous_class(self):
        result = self.register([
            self.schedule(), self.schedule(class_name='Bad time', start_time='12:00', end_time='11:00'),
        ])
        self.assertFalse(result['success'])
        self.assert_no_registration()

    def test_overlapping_class_rolls_back_everything(self):
        result = self.register([
            self.schedule(),
            self.schedule(class_name='Overlap', day='Wednesday', start_time='09:30', end_time='10:30'),
        ])
        self.assertFalse(result['success'])
        self.assertIn('overlaps', result['message'])
        self.assert_no_registration()

    def test_duplicate_class_rolls_back_everything(self):
        result = self.register([self.schedule(), self.schedule(day='Friday')])
        self.assertFalse(result['success'])
        self.assert_no_registration()

    def test_unlisted_building_and_missing_days_are_rejected(self):
        for changes in ({'building': 'Unknown'}, {'day': ''}):
            with self.subTest(changes=changes):
                self.assertFalse(self.register([self.schedule(**changes)])['success'])
                self.assert_no_registration()

    def test_last_name_is_required(self):
        self.assertFalse(self.register([], last_name='')['success'])
        self.assert_no_registration()

    def test_account_without_classes(self):
        result = self.register([])
        self.assertTrue(result['success'], result)
        self.assertEqual(database.get_user_schedule(result['user_id']), [])

    def test_existing_standalone_database_functions_still_commit(self):
        result = database.add_user('Test', 'Student', 'other@example.com', 'Password!')
        self.assertTrue(result['success'])
        self.assertTrue(database.add_schedule(result['user_id'], **self.schedule())['success'])
        self.assertEqual(len(database.get_user_schedule(result['user_id'])), 1)

    def test_form_validates_passwords_and_submits_only_remaining_rows(self):
        from nicegui import ui
        from frontend.components.class_schedule_row import class_schedule_row
        from frontend.components.registration_form import registration_form

        callbacks = {}
        created_rows = []
        registered_emails = []
        original_button = ui.button

        def button(*args, **kwargs):
            if args and args[0] in ('Create account', 'Add class'):
                callbacks[args[0]] = kwargs['on_click']
            return original_button(*args, **kwargs)

        def create_row(buildings):
            row = class_schedule_row(buildings)
            created_rows.append(row)
            return row

        async def execute(function, *args):
            return function(*args)

        with patch.object(ui, 'button', side_effect=button), patch(
            'frontend.components.registration_form.class_schedule_row', side_effect=create_row
        ), patch('frontend.components.registration_form.run.io_bound', side_effect=execute):
            with ui.column() as form:
                registration_form(on_registered=registered_emails.append)

            inputs = {e._props['placeholder']: e for e in form.descendants()
                      if 'placeholder' in e._props}
            inputs['First Name'].set_value(' Test ')
            inputs['Last Name'].set_value(' Student ')
            inputs['Email'].set_value(' student@example.com ')
            inputs['Password'].set_value('Test password!')
            inputs['Confirm Password'].set_value('Mismatch')
            row = created_rows[0]
            row.class_name.set_value('CECS 101')
            row.building.set_value('Engineering')
            row.days.update({'Wednesday', 'Monday'})
            row.start_time.set_value('09:00')
            row.end_time.set_value('10:00')

            async def submit_form():
                with form:
                    await callbacks['Create account']()

            with form:
                asyncio.run(submit_form())
                self.assert_no_registration()
                self.assertTrue(any(getattr(e, 'text', '') == 'The passwords do not match.'
                                    for e in form.descendants()))

                inputs['Confirm Password'].set_value('Test password!')
                callbacks['Add class']()
                created_rows[-1].container.delete()
                asyncio.run(submit_form())

            self.assertEqual(registered_emails, ['student@example.com'])
            user_id = database.get_user_id('student@example.com')
            schedules = database.get_user_schedule(user_id)
            self.assertEqual(len(schedules), 1)
            self.assertEqual(schedules[0][4], 'Monday/Wednesday')
            self.assertEqual(inputs['Password'].value, '')
            form.delete()


if __name__ == '__main__':
    unittest.main()
