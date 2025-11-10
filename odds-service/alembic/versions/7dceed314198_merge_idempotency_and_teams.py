"""merge_idempotency_and_teams

Revision ID: 7dceed314198
Revises: 39a6a5bedbcc, e6_events_idempotency
Create Date: 2025-11-10 20:20:49.961478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dceed314198'
down_revision: Union[str, Sequence[str], None] = ('39a6a5bedbcc', 'e6_events_idempotency')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
