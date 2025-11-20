"""merge_all_heads

Revision ID: 39a6a5bedbcc
Revises: e5_events_flexible_participants, a7f4627de072
Create Date: 2025-11-10 18:16:07.729623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39a6a5bedbcc'
down_revision: Union[str, Sequence[str], None] = ('e5_events_flexible_participants', 'a7f4627de072')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
