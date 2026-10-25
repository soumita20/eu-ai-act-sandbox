"""Uvicorn entry point for the configured sandbox API."""

from .bootstrap import create_configured_app

app = create_configured_app()
