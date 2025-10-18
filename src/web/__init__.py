"""
Web interface for PostgreSQL Backup & Restore Tool
"""

from .app import create_app

__all__ = ['create_app']