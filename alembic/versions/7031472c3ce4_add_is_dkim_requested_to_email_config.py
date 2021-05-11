"""add is dkim requested to email config

Revision ID: 7031472c3ce4
Revises: e61641507a04
Create Date: 2021-05-07 10:14:31.793945

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7031472c3ce4'
down_revision = 'e61641507a04'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('email_config', sa.Column('is_ses_dkim_requested', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('email_config', 'is_ses_dkim_requested')
    # ### end Alembic commands ###