"""
Database table creation from SQLAlchemy models.
Run this to create all tables without manual SQL.

Usage:
    python -m backend.app.create_tables
"""

from app.database import engine, Base
from app.models import *  # noqa: F401, F403 - import all models to register them


def create_all_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. All tables created successfully.")

    # Print table list
    from app.models import __all__
    print(f"\nTables created ({len(__all__)}):")
    for name in __all__:
        print(f"  - {name}")


if __name__ == "__main__":
    create_all_tables()
