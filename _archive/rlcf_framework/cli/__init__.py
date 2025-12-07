"""
RLCF Command Line Interface

Provides command-line tools for RLCF operations:
- rlcf-cli: User-facing commands (tasks, users, feedback)
- rlcf-admin: Administrative commands (config, db, server)
"""

from .commands import cli, admin

__all__ = ['cli', 'admin']
