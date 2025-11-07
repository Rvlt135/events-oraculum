"""Initial migration with auth models

Revision ID: 2b0cec39e646
Revises: 
Create Date: 2025-10-21 20:40:44.293573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b0cec39e646'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enum types will be created automatically by SQLAlchemy
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('plan_type', sa.Enum('free', 'pro', 'partner', name='plantype'), nullable=False),
        sa.Column('trial_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('telegram_account_id', sa.BigInteger(), nullable=True),
        sa.Column('telegram_is_premium', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_telegram_account_id'), 'users', ['telegram_account_id'], unique=True)
    
    # Create user_identities table
    op.create_table('user_identities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.Enum('google', 'password', 'telegram', name='identityprovider'), nullable=False),
        sa.Column('provider_user_id', sa.Text(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('first_name', sa.Text(), nullable=True),
        sa.Column('last_name', sa.Text(), nullable=True),
        sa.Column('language_code', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.Text(), nullable=True),
        sa.Column('is_premium', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_identities_user_id'), 'user_identities', ['user_id'], unique=False)
    
    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('jti', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('jti')
    )
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables
    op.drop_table('user_sessions')
    op.drop_table('user_identities')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS identityprovider")
    op.execute("DROP TYPE IF EXISTS plantype")
