"""add streak fields and user_badges table

Revision ID: a1b2c3d4e5f6
Revises: e87c8be47b88
Create Date: 2026-05-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e87c8be47b88'
branch_labels = None
depends_on = None


def upgrade():
    # Add streak columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_streak', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('longest_streak', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('last_quiz_date', sa.Date(), nullable=True))

    # Create user_badges table
    op.create_table(
        'user_badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('badge_key', sa.String(length=50), nullable=False),
        sa.Column('earned_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'badge_key', name='uq_user_badge'),
    )


def downgrade():
    op.drop_table('user_badges')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_quiz_date')
        batch_op.drop_column('longest_streak')
        batch_op.drop_column('current_streak')
