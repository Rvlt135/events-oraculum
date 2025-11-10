"""
E4: Teams table sport-scoped unique constraint

- Replace global UNIQUE(normalized_name) with UNIQUE(sport_id, normalized_name)
- Update index to composite (sport_id, normalized_name)

Revision ID: e4_teams_sport_scoped_unique
Revises: e4_events_multi_provider
Create Date: 2025-11-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4_teams_sport_scoped_unique'
down_revision = 'e4_events_multi_provider'
branch_labels = None
depends_on = None


def upgrade():
    """Apply E4 teams table changes."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Step 1: Drop old unique constraint on normalized_name if it exists
    constraints = inspector.get_unique_constraints('teams')
    indexes = inspector.get_indexes('teams')

    # Check for unique constraint on normalized_name
    for constraint in constraints:
        if constraint['column_names'] == ['normalized_name']:
            op.drop_constraint(constraint['name'], 'teams', type_='unique')
            break

    # Also check for unique index (SQLAlchemy unique=True creates an index)
    for index in indexes:
        if index['column_names'] == ['normalized_name'] and index.get('unique'):
            op.drop_index(index['name'], table_name='teams')
            break

    # Step 2: Create new composite unique constraint on (sport_id, normalized_name)
    # Check if it already exists
    has_composite_unique = False
    for constraint in inspector.get_unique_constraints('teams'):
        if set(constraint['column_names']) == {'sport_id', 'normalized_name'}:
            has_composite_unique = True
            break

    if not has_composite_unique:
        op.create_unique_constraint(
            'uq_teams_sport_normalized_name',
            'teams',
            ['sport_id', 'normalized_name']
        )

    # Step 3: Update index on normalized_name to be composite if needed
    # Drop old single-column index if it exists
    for index in indexes:
        if index['column_names'] == ['normalized_name'] and not index.get('unique'):
            op.drop_index(index['name'], table_name='teams')
            break

    # Create composite index if it doesn't exist
    has_composite_index = False
    for index in indexes:
        if index['column_names'] == ['sport_id', 'normalized_name']:
            has_composite_index = True
            break

    if not has_composite_index:
        op.create_index(
            'idx_teams_sport_normalized_name',
            'teams',
            ['sport_id', 'normalized_name'],
            unique=False
        )


def downgrade():
    """Revert E4 teams table changes."""

    # Step 1: Drop composite index
    try:
        op.drop_index('idx_teams_sport_normalized_name', table_name='teams')
    except Exception:
        pass  # Index might not exist

    # Step 2: Drop composite unique constraint
    try:
        op.drop_constraint('uq_teams_sport_normalized_name', 'teams', type_='unique')
    except Exception:
        pass  # Constraint might not exist

    # Step 3: Re-create unique constraint on normalized_name alone
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = inspector.get_indexes('teams')

    has_normalized_name_unique = False
    for index in indexes:
        if index['column_names'] == ['normalized_name'] and index.get('unique'):
            has_normalized_name_unique = True
            break

    if not has_normalized_name_unique:
        op.create_unique_constraint('uq_teams_normalized_name', 'teams', ['normalized_name'])

    # Step 4: Re-create index on normalized_name
    has_normalized_name_index = False
    for index in indexes:
        if index['column_names'] == ['normalized_name'] and not index.get('unique'):
            has_normalized_name_index = True
            break

    if not has_normalized_name_index:
        op.create_index('idx_teams_normalized_name', 'teams', ['normalized_name'], unique=False)
