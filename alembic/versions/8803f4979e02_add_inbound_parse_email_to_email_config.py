"""add inbound_parse_email to email_config

Revision ID: 8803f4979e02
Revises: e685fce993a0
Create Date: 2021-08-26 14:26:59.871364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8803f4979e02'
down_revision = 'e685fce993a0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('email_config', sa.Column('inbound_parse_email', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('email_config', 'inbound_parse_email')
    # ### end Alembic commands ###
