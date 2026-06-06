"""initial

Revision ID: e15bee0df862
Revises: 
Create Date: 2026-06-06 12:42:57.321883

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e15bee0df862'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # No-op migration: schema already matches models in the existing SQLite file.
    # Adjust manually if you need schema changes.
    pass


def downgrade():
    # No-op downgrade for the initial revision.
    pass
