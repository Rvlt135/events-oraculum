"""merge_plan_visibility_and_e4_migrations

Revision ID: fcd3c0bb3357
Revises: 1aa10f446e6f, e4_teams_sport_scoped_unique
Create Date: 2025-11-10 17:53:22.129534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcd3c0bb3357'
down_revision: Union[str, Sequence[str], None] = ('1aa10f446e6f', 'e4_teams_sport_scoped_unique')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
