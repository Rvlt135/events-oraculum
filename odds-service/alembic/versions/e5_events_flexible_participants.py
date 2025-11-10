"""
E5: Events flexible participants support

- Make home_team_id, away_team_id, home_team_name, away_team_name NULLABLE
- Add participant_mode TEXT with CHECK constraint
- Add participants JSONB field for flexible participant storage

Revision ID: e5_events_flexible_participants
Revises: e4_teams_sport_scoped_unique
Create Date: 2025-11-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e5_events_flexible_participants'
down_revision = 'e4_teams_sport_scoped_unique'
branch_labels = None
depends_on = None


def upgrade():
    """Apply E5 events table changes for flexible participants."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col['name']: col for col in inspector.get_columns('events')}

    # Step 1: Make team fields nullable if they exist and are NOT NULL
    team_fields = ['home_team_id', 'away_team_id']
    for field in team_fields:
        if field in columns and not columns[field].get('nullable', True):
            op.alter_column('events', field, nullable=True)

    # Step 2: Add home_team_name and away_team_name if they don't exist
    if 'home_team_name' not in columns:
        op.add_column('events',
            sa.Column('home_team_name', sa.Text(), nullable=True)
        )

    if 'away_team_name' not in columns:
        op.add_column('events',
            sa.Column('away_team_name', sa.Text(), nullable=True)
        )

    # Step 3: Add participant_mode with CHECK constraint
    if 'participant_mode' not in columns:
        op.add_column('events',
            sa.Column('participant_mode', sa.Text(), nullable=False, server_default='unknown')
        )
        # Remove server_default after adding
        op.alter_column('events', 'participant_mode', server_default=None)

        # Add CHECK constraint
        op.execute("""
            ALTER TABLE events ADD CONSTRAINT chk_events_participant_mode
            CHECK (participant_mode IN ('duel', 'solo', 'field', 'unknown'))
        """)

    # Step 4: Add participants JSONB field
    if 'participants' not in columns:
        op.add_column('events',
            sa.Column('participants', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]')
        )
        # Remove server_default after adding
        op.alter_column('events', 'participants', server_default=None)


def downgrade():
    """Revert E5 events table changes."""

    # Step 1: Drop participants column
    try:
        op.drop_column('events', 'participants')
    except Exception:
        pass

    # Step 2: Drop participant_mode and its constraint
    try:
        op.execute("ALTER TABLE events DROP CONSTRAINT IF EXISTS chk_events_participant_mode")
    except Exception:
        pass

    try:
        op.drop_column('events', 'participant_mode')
    except Exception:
        pass

    # Step 3: Drop team name columns
    try:
        op.drop_column('events', 'away_team_name')
    except Exception:
        pass

    try:
        op.drop_column('events', 'home_team_name')
    except Exception:
        pass

    # Step 4: Make team_id fields NOT NULL again (if data allows)
    # Note: This may fail if there are NULL values - manual intervention needed
    try:
        op.alter_column('events', 'away_team_id', nullable=False)
    except Exception:
        pass

    try:
        op.alter_column('events', 'home_team_id', nullable=False)
    except Exception:
        pass
