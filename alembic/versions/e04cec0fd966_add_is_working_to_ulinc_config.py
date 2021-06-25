"""add is_working to ulinc_config

Revision ID: e04cec0fd966
Revises: adabc1b8d66b
Create Date: 2021-06-24 09:10:02.439686

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e04cec0fd966'
down_revision = 'adabc1b8d66b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ulinc_config', sa.Column('is_working', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ulinc_config', 'is_working')
    # ### end Alembic commands ###