"""add is_polling_ulinc flag to account

Revision ID: ec63aa69a28a
Revises: ba0419e256f4
Create Date: 2021-07-26 11:51:08.439076

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec63aa69a28a'
down_revision = 'ba0419e256f4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('is_polling_ulinc', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('account', 'is_polling_ulinc')
    # ### end Alembic commands ###
