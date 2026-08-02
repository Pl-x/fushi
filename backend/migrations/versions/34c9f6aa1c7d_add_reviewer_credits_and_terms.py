"""add reviewer credits and terms acceptance

Revision ID: 34c9f6aa1c7d
Revises: beb0c96b8980
"""
from alembic import op
import sqlalchemy as sa


revision = '34c9f6aa1c7d'
down_revision = 'beb0c96b8980'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('terms_version', sa.String(length=20), nullable=True))
    op.add_column('payments', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('payments', sa.Column('purpose', sa.String(length=40), nullable=True))
    op.create_foreign_key('fk_payments_user_id_users', 'payments', 'users', ['user_id'], ['id'])
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_table(
        'credit_ledger',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount_units', sa.Integer(), nullable=False),
        sa.Column('entry_type', sa.String(length=30), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('review_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
        sa.ForeignKeyConstraint(['review_id'], ['hotel_reviews.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_id'),
        sa.UniqueConstraint('review_id'),
    )
    op.create_index('ix_credit_ledger_user_id', 'credit_ledger', ['user_id'])


def downgrade():
    op.drop_index('ix_credit_ledger_user_id', table_name='credit_ledger')
    op.drop_table('credit_ledger')
    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_constraint('fk_payments_user_id_users', 'payments', type_='foreignkey')
    op.drop_column('payments', 'purpose')
    op.drop_column('payments', 'user_id')
    op.drop_column('users', 'terms_version')
    op.drop_column('users', 'terms_accepted_at')
