"""update_teams_table_changes

Revision ID: a7f4627de072
Revises: fcd3c0bb3357
Create Date: 2025-11-10 18:12:21.986309

Ensure teams table has correct structure matching ORM model:
- Composite unique constraint on (sport_id, normalized_name)
- Composite index on (sport_id, normalized_name)
- Index on sport_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7f4627de072'
down_revision: Union[str, Sequence[str], None] = 'fcd3c0bb3357'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure teams table structure matches ORM model."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check and create composite unique constraint if missing
    constraints = inspector.get_unique_constraints('teams')
    has_composite_unique = False
    for constraint in constraints:
        if set(constraint['column_names']) == {'sport_id', 'normalized_name'}:
            has_composite_unique = True
            break

    if not has_composite_unique:
        op.create_unique_constraint(
            'uq_teams_sport_normalized_name',
            'teams',
            ['sport_id', 'normalized_name']
        )

    # Check and create indexes if missing
    indexes = inspector.get_indexes('teams')
    
    # Check for sport_id index
    has_sport_id_index = False
    for index in indexes:
        if index['column_names'] == ['sport_id']:
            has_sport_id_index = True
            break
    
    if not has_sport_id_index:
        op.create_index('idx_teams_sport_id', 'teams', ['sport_id'])

    # Check for composite index on (sport_id, normalized_name)
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


def downgrade() -> None:
    """Revert teams table changes."""
    # Note: This is a safety migration, so downgrade is minimal
    # The actual structure changes were made in e4_teams_sport_scoped_unique
    pass
