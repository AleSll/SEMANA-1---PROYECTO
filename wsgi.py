"""Punto de entrada WSGI (gunicorn wsgi:app / PythonAnywhere / Render)."""
from backend.app import crear_app

app = crear_app()
