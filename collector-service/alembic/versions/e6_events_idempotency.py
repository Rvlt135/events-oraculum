"""
E6: Events idempotency and tracking

- Add ingested_at and last_seen_at timestamps for tracking
- Support idempotent upserts with proper conflict handling

Revision ID: e6_events_idempotency
Revises: e5_events_flexible_participants
Create Date: 2025-11-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'e6_events_idempotency'
down_revision = 'e5_events_flexible_participants'
branch_labels = None
depends_on = None


def upgrade():
    """Add ingested_at and last_seen_at columns."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col['name']: col for col in inspector.get_columns('events')}

    # Add ingested_at if it doesn't exist
    if 'ingested_at' not in columns:
        op.add_column('events',
            sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=True)
        )
        # Set default for existing rows
        op.execute("UPDATE events SET ingested_at = created_at WHERE ingested_at IS NULL")

    # Add last_seen_at if it doesn't exist
    if 'last_seen_at' not in columns:
        op.add_column('events',
            sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True)
        )
        # Set default for existing rows
        op.execute("UPDATE events SET last_seen_at = created_at WHERE last_seen_at IS NULL")


def downgrade():
    """Remove ingested_at and last_seen_at columns."""

    try:
        op.drop_column('events', 'last_seen_at')
    except Exception:
        pass

    try:
        op.drop_column('events', 'ingested_at')
    except Exception:
        pass
