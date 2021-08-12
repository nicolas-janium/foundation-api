"""add ulinc campaign origin message table

Revision ID: 28475d852b78
Revises: be70a02523dd
Create Date: 2021-08-12 12:56:20.891025

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '28475d852b78'
down_revision = 'be70a02523dd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ulinc_campaign_origin_message',
    sa.Column('ulinc_campaign_origin_message_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_campaign_id', sa.String(length=36), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_messenger', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['ulinc_campaign_id'], ['ulinc_campaign.ulinc_campaign_id'], ),
    sa.PrimaryKeyConstraint('ulinc_campaign_origin_message_id')
    )
    op.add_column('user', sa.Column('parse_email', sa.String(length=256), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'parse_email')
    op.drop_table('ulinc_campaign_origin_message')
    # ### end Alembic commands ###
