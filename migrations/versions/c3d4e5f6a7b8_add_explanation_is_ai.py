"""add explanation_is_ai to questions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('explanation_is_ai', sa.Boolean(), nullable=True, server_default='false')
        )


def downgrade():
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.drop_column('explanation_is_ai')
