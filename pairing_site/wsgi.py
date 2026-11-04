"""The entry point the application server loads: `gunicorn pairing_site.wsgi:app`."""

from .app import create_app

app = create_app()
