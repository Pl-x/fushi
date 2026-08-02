"""add reviewer comments

Revision ID: 9fb784ce214a
Revises: 34c9f6aa1c7d
"""
from alembic import op
import sqlalchemy as sa

revision = '9fb784ce214a'
down_revision = '34c9f6aa1c7d'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('hotel_reviews', sa.Column('comment', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('hotel_reviews', 'comment')
