#!/usr/bin/env python3
"""
Script for initializing database from scratch.

This script applies the initial migration to create all tables.
Useful for fresh deployments and local development setup.

Usage:
    python scripts/init_db.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from app.config.settings import settings


def init_database():
    """Initialize database with all tables."""
    print("Initializing database...")
    print(f"Database URL: {settings.postgres_url.split('@')[1] if '@' in settings.postgres_url else 'hidden'}")
    
    # Configure Alembic
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option('sqlalchemy.url', str(settings.postgres_url + "?async_fallback=True"))
    
    # Apply initial migration (creates all tables)
    print("\nApplying initial migration (55aabbccddee)...")
    try:
        command.upgrade(alembic_cfg, "55aabbccddee")
        print("✓ Initial migration applied successfully")
    except Exception as e:
        print(f"✗ Error applying initial migration: {e}")
        print("\nTrying to apply all migrations instead...")
        try:
            command.upgrade(alembic_cfg, "head")
            print("✓ All migrations applied successfully")
        except Exception as e2:
            print(f"✗ Error: {e2}")
            sys.exit(1)
    
    # Check current revision
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(alembic_cfg)
    current = script.get_current_head()
    print(f"\nCurrent database revision: {current}")
    print("\n✓ Database initialization complete!")


if __name__ == "__main__":
    init_database()

