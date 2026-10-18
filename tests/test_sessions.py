import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from nicegui import app
from nicegui.storage import RequestTrackingMiddleware, Storage
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from frontend.config import get_storage_secret
from frontend.components.navbar import logout


class StorageSecretTests(unittest.TestCase):
    def test_local_secret_is_generated_once_and_reused(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch(
            'frontend.config.STORAGE_SECRET_FILE', Path(directory) / '.nicegui' / 'storage_secret'
        ):
            secret = get_storage_secret()
            self.assertGreaterEqual(len(secret), 32)
            self.assertEqual(get_storage_secret(), secret)

    def test_environment_overrides_local_file(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_file = Path(directory) / 'storage_secret'
            with patch.dict(os.environ, {'CAMPUS_ROUTE_STORAGE_SECRET': 'test-environment-secret'}), patch(
                'frontend.config.STORAGE_SECRET_FILE', secret_file
            ):
                self.assertEqual(get_storage_secret(), 'test-environment-secret')
                self.assertFalse(secret_file.exists())


class SessionIsolationTests(unittest.TestCase):
    def test_cookie_keeps_identity_across_requests_and_isolates_browsers(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            Storage, 'path', Path(directory)
        ), patch.object(app.storage, '_users', {}), patch('nicegui.core.script_mode', False), patch(
            'frontend.components.navbar.ui.navigate.to'
        ):
            server = FastAPI(middleware=[
                Middleware(SessionMiddleware, secret_key='test-session-secret'),
                Middleware(RequestTrackingMiddleware),
            ])

            @server.post('/set-identity/{user_id}')
            async def set_identity(user_id: int):
                app.storage.user['user_id'] = user_id
                return {'user_id': user_id}

            @server.get('/identity')
            async def identity():
                return {'user_id': app.storage.user.get('user_id')}

            @server.post('/logout')
            async def end_session():
                logout()
                return {'success': True}

            with TestClient(server) as first, TestClient(server) as second:
                self.assertIsNone(first.get('/identity').json()['user_id'])
                self.assertIsNone(second.get('/identity').json()['user_id'])
                first.post('/set-identity/11').raise_for_status()
                second.post('/set-identity/22').raise_for_status()
                self.assertEqual(first.get('/identity').json()['user_id'], 11)
                self.assertEqual(second.get('/identity').json()['user_id'], 22)

                # The cookie contains the browser session ID, not the user's password or account ID.
                cookie = first.cookies.get('session')
                with TestClient(server, cookies={'session': cookie}) as another_tab:
                    self.assertEqual(another_tab.get('/identity').json()['user_id'], 11)

                # Simulate reloading persisted server storage on a later request.
                app.storage._users.clear()
                self.assertEqual(first.get('/identity').json()['user_id'], 11)
                self.assertEqual(second.get('/identity').json()['user_id'], 22)

                first.post('/logout').raise_for_status()
                self.assertIsNone(first.get('/identity').json()['user_id'])
                self.assertEqual(second.get('/identity').json()['user_id'], 22)
                with TestClient(server, cookies={'session': cookie}) as logged_out_tab:
                    self.assertIsNone(logged_out_tab.get('/identity').json()['user_id'])


if __name__ == '__main__':
    unittest.main()
