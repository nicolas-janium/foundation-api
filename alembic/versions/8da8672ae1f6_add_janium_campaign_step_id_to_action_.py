"""add janium_campaign_step_id to action table

Revision ID: 8da8672ae1f6
Revises: 8803f4979e02
Create Date: 2021-09-09 09:22:30.790408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8da8672ae1f6'
down_revision = '8803f4979e02'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('action', sa.Column('janium_campaign_step_id', sa.String(length=36), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('action', 'janium_campaign_step_id')
    # ### end Alembic commands ###
