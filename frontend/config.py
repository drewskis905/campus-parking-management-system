import os
import secrets
from pathlib import Path


STORAGE_SECRET_FILE = Path(__file__).resolve().parent.parent / '.nicegui' / 'storage_secret'


def get_storage_secret() -> str:
    """Use the configured secret, or persist a private key for local runs."""
    configured = os.environ.get('CAMPUS_ROUTE_STORAGE_SECRET', '').strip()
    if configured:
        return configured

    STORAGE_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_SECRET_FILE.exists():
        STORAGE_SECRET_FILE.write_text(secrets.token_urlsafe(32), encoding='utf-8')
    secret = STORAGE_SECRET_FILE.read_text(encoding='utf-8').strip()
    if not secret:
        raise RuntimeError('The storage secret file is empty. Set CAMPUS_ROUTE_STORAGE_SECRET.')
    return secret
