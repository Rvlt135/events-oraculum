"""
E4: Events table multi-provider support

- Add provider column with default 'odds_api'
- Replace UNIQUE(external_id) with UNIQUE(provider, external_id)
- Add composite index (competition_id, commence_time) for window queries

Revision ID: e4_events_multi_provider
Revises: 55aabbccddee
Create Date: 2025-11-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e4_events_multi_provider'
down_revision = '55aabbccddee'
branch_labels = None
depends_on = None


def upgrade():
    """Apply E4 events table changes."""

    # Step 1: Add provider column with default 'odds_api' if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('events')]

    if 'provider' not in columns:
        op.add_column('events',
            sa.Column('provider', sa.Text(), nullable=False, server_default='odds_api')
        )
        # Remove server_default after adding (keep default in ORM only)
        op.alter_column('events', 'provider', server_default=None)

    # Step 2: Drop old unique constraint on external_id if it exists
    constraints = inspector.get_unique_constraints('events')
    indexes = inspector.get_indexes('events')

    # Check if there's a unique constraint or unique index on external_id
    for constraint in constraints:
        if constraint['column_names'] == ['external_id']:
            op.drop_constraint(constraint['name'], 'events', type_='unique')
            break

    # Also check for unique index (SQLAlchemy unique=True creates an index)
    for index in indexes:
        if index['column_names'] == ['external_id'] and index.get('unique'):
            op.drop_index(index['name'], table_name='events')
            break

    # Step 3: Create new composite unique constraint on (provider, external_id)
    # Check if it already exists
    has_composite_unique = False
    for constraint in inspector.get_unique_constraints('events'):
        if set(constraint['column_names']) == {'provider', 'external_id'}:
            has_composite_unique = True
            break

    if not has_composite_unique:
        op.create_unique_constraint(
            'uq_events_provider_external_id',
            'events',
            ['provider', 'external_id']
        )

    # Step 4: Add composite index (competition_id, commence_time) for window queries
    # Check if it already exists
    has_composite_index = False
    for index in indexes:
        if index['column_names'] == ['competition_id', 'commence_time']:
            has_composite_index = True
            break

    if not has_composite_index:
        op.create_index(
            'idx_events_competition_commence',
            'events',
            ['competition_id', 'commence_time'],
            unique=False
        )


def downgrade():
    """Revert E4 events table changes."""

    # Step 1: Drop composite index
    try:
        op.drop_index('idx_events_competition_commence', table_name='events')
    except Exception:
        pass  # Index might not exist

    # Step 2: Drop composite unique constraint
    try:
        op.drop_constraint('uq_events_provider_external_id', 'events', type_='unique')
    except Exception:
        pass  # Constraint might not exist

    # Step 3: Re-create unique constraint on external_id
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = inspector.get_indexes('events')

    has_external_id_unique = False
    for index in indexes:
        if index['column_names'] == ['external_id'] and index.get('unique'):
            has_external_id_unique = True
            break

    if not has_external_id_unique:
        op.create_unique_constraint('uq_events_external_id', 'events', ['external_id'])

    # Step 4: Drop provider column
    try:
        op.drop_column('events', 'provider')
    except Exception:
        pass  # Column might not exist
