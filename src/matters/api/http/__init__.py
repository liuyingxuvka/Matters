"""Dependency-injected HTTP projection package."""

from matters.api.http.app import MattersHTTP, application, create_application
from matters.api.http.static import LocalUI, create_local_application

__all__ = [
    "LocalUI",
    "MattersHTTP",
    "application",
    "create_application",
    "create_local_application",
]
