"""add plan_visibility to sports and competitions

Revision ID: 1aa10f446e6f
Revises: 55aabbccddee
Create Date: 2025-11-08 21:35:32.341975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1aa10f446e6f'
down_revision: Union[str, Sequence[str], None] = '55aabbccddee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add plan_visibility column to sports table
    op.add_column('sports', sa.Column('plan_visibility', sa.Text(), nullable=False, server_default='free'))
    
    # Add plan_visibility column to competitions table
    op.add_column('competitions', sa.Column('plan_visibility', sa.Text(), nullable=False, server_default='free'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove plan_visibility column from competitions table
    op.drop_column('competitions', 'plan_visibility')
    
    # Remove plan_visibility column from sports table
    op.drop_column('sports', 'plan_visibility')
