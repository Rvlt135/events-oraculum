"""create_agent_analysis_outputs_table

Revision ID: 3d648547d913
Revises: 
Create Date: 2025-12-11 10:41:18.625911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3d648547d913'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'agent_analysis_outputs',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('outputs_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('main_score', sa.Float(), nullable=False),
        sa.Column('decision', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('event_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('agent_analysis_outputs')
