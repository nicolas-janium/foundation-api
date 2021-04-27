"""add email_message_id to action table

Revision ID: 220cd5796cd6
Revises: f58b21af3230
Create Date: 2021-04-27 10:24:38.512186

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '220cd5796cd6'
down_revision = 'f58b21af3230'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('action', sa.Column('email_message_id', sa.String(length=512), nullable=True))


def downgrade():
     op.drop_column('action', 'email_message_id')
