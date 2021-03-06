"""first revision

Revision ID: 7456095e65c9
Revises: 
Create Date: 2021-06-17 11:55:52.491193

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7456095e65c9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('action_type',
    sa.Column('action_type_id', sa.Integer(), nullable=False),
    sa.Column('action_type_name', sa.String(length=64), nullable=False),
    sa.Column('action_type_description', sa.String(length=512), nullable=False),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('action_type_id')
    )
    op.create_table('contact_source_type',
    sa.Column('contact_source_type_id', sa.Integer(), nullable=False),
    sa.Column('contact_source_type_name', sa.String(length=128), nullable=False),
    sa.Column('contact_source_type_description', sa.String(length=256), nullable=False),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('contact_source_type_id')
    )
    op.create_table('cookie_type',
    sa.Column('cookie_type_id', sa.Integer(), nullable=False),
    sa.Column('cookie_type_name', sa.String(length=128), nullable=False),
    sa.Column('cookie_type_description', sa.String(length=256), nullable=True),
    sa.Column('cookie_type_website_url', sa.String(length=512), nullable=True),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('cookie_type_id')
    )
    op.create_table('credentials',
    sa.Column('credentials_id', sa.String(length=36), nullable=False),
    sa.Column('username', sa.String(length=256), nullable=False),
    sa.Column('password', sa.String(length=256), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.PrimaryKeyConstraint('credentials_id')
    )
    op.create_table('dte',
    sa.Column('dte_id', sa.String(length=36), nullable=False),
    sa.Column('dte_name', sa.String(length=128), nullable=False),
    sa.Column('dte_description', sa.String(length=256), nullable=True),
    sa.Column('dte_subject', sa.String(length=512), nullable=False),
    sa.Column('dte_body', sa.Text(), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.PrimaryKeyConstraint('dte_id')
    )
    op.create_table('email_server',
    sa.Column('email_server_id', sa.String(length=36), nullable=False),
    sa.Column('email_server_name', sa.String(length=64), nullable=False),
    sa.Column('smtp_address', sa.String(length=64), nullable=False),
    sa.Column('smtp_tls_port', sa.Integer(), nullable=False),
    sa.Column('smtp_ssl_port', sa.Integer(), nullable=False),
    sa.Column('imap_address', sa.String(length=64), nullable=False),
    sa.Column('imap_ssl_port', sa.Integer(), nullable=False),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('email_server_id')
    )
    op.create_table('janium_campaign_step_type',
    sa.Column('janium_campaign_step_type_id', sa.Integer(), nullable=False),
    sa.Column('janium_campaign_step_type_name', sa.String(length=64), nullable=False),
    sa.Column('janium_campaign_step_type_description', sa.String(length=512), nullable=False),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('janium_campaign_step_type_id')
    )
    op.create_table('time_zone',
    sa.Column('time_zone_id', sa.String(length=36), nullable=False),
    sa.Column('time_zone_name', sa.String(length=64), nullable=False),
    sa.Column('time_zone_code', sa.String(length=16), nullable=False),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('time_zone_id')
    )
    op.create_table('cookie',
    sa.Column('cookie_id', sa.String(length=36), nullable=False),
    sa.Column('cookie_type_id', sa.Integer(), nullable=True),
    sa.Column('cookie_json_value', sa.JSON(), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.Column('effective_start_date', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('effective_end_date', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['cookie_type_id'], ['cookie_type.cookie_type_id'], ),
    sa.PrimaryKeyConstraint('cookie_id')
    )
    op.create_table('user',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('credentials_id', sa.String(length=36), nullable=False),
    sa.Column('first_name', sa.String(length=126), nullable=False),
    sa.Column('last_name', sa.String(length=126), nullable=False),
    sa.Column('full_name', sa.String(length=256), sa.Computed("CONCAT(first_name, ' ', last_name)", ), nullable=True),
    sa.Column('title', sa.String(length=256), nullable=True),
    sa.Column('company', sa.String(length=256), nullable=True),
    sa.Column('location', sa.String(length=256), nullable=True),
    sa.Column('primary_email', sa.String(length=256), nullable=False),
    sa.Column('phone', sa.String(length=256), nullable=True),
    sa.Column('additional_contact_info', sa.JSON(), nullable=True),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['credentials_id'], ['credentials.credentials_id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('account',
    sa.Column('account_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('time_zone_id', sa.String(length=36), nullable=False),
    sa.Column('dte_id', sa.String(length=36), nullable=False),
    sa.Column('is_sending_emails', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_sending_li_messages', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_receiving_dte', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.Column('effective_start_date', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('effective_end_date', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.Column('data_enrichment_start_date', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('data_enrichment_end_date', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['dte_id'], ['dte.dte_id'], ),
    sa.ForeignKeyConstraint(['time_zone_id'], ['time_zone.time_zone_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('account_id')
    )
    op.create_table('email_config',
    sa.Column('email_config_id', sa.String(length=36), nullable=False),
    sa.Column('account_id', sa.String(length=36), nullable=True),
    sa.Column('credentials_id', sa.String(length=36), nullable=True),
    sa.Column('email_server_id', sa.String(length=36), nullable=True),
    sa.Column('from_full_name', sa.String(length=64), nullable=False),
    sa.Column('from_address', sa.String(length=64), nullable=False),
    sa.Column('reply_to_address', sa.String(length=64), nullable=False),
    sa.Column('is_sendgrid', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_sendgrid_domain_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_smtp', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_ses', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_ses_dkim_requested', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_ses_dkim_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_ses_domain_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_email_forward', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_email_forward_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_reply_proxy', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.account_id'], ),
    sa.ForeignKeyConstraint(['credentials_id'], ['credentials.credentials_id'], ),
    sa.ForeignKeyConstraint(['email_server_id'], ['email_server.email_server_id'], ),
    sa.PrimaryKeyConstraint('email_config_id')
    )
    op.create_table('ulinc_config',
    sa.Column('ulinc_config_id', sa.String(length=36), nullable=False),
    sa.Column('credentials_id', sa.String(length=36), nullable=False),
    sa.Column('cookie_id', sa.String(length=36), nullable=False),
    sa.Column('account_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_client_id', sa.String(length=16), nullable=False),
    sa.Column('ulinc_li_email', sa.String(length=64), nullable=False),
    sa.Column('ulinc_is_active', sa.Boolean(), nullable=False),
    sa.Column('new_connection_webhook', sa.String(length=256), nullable=False),
    sa.Column('new_message_webhook', sa.String(length=256), nullable=False),
    sa.Column('send_message_webhook', sa.String(length=256), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.account_id'], ),
    sa.ForeignKeyConstraint(['cookie_id'], ['cookie.cookie_id'], ),
    sa.ForeignKeyConstraint(['credentials_id'], ['credentials.credentials_id'], ),
    sa.PrimaryKeyConstraint('ulinc_config_id')
    )
    op.create_table('contact_source',
    sa.Column('contact_source_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_config_id', sa.String(length=36), nullable=False),
    sa.Column('contact_source_type_id', sa.Integer(), nullable=False),
    sa.Column('contact_source_json', sa.JSON(), nullable=False),
    sa.Column('is_processed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['ulinc_config_id'], ['ulinc_config.ulinc_config_id'], ),
    sa.ForeignKeyConstraint(['contact_source_type_id'], ['contact_source_type.contact_source_type_id'], ),
    sa.PrimaryKeyConstraint('contact_source_id')
    )
    op.create_table('janium_campaign',
    sa.Column('janium_campaign_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_config_id', sa.String(length=36), nullable=False),
    sa.Column('email_config_id', sa.String(length=36), nullable=False),
    sa.Column('janium_campaign_name', sa.String(length=512), nullable=False),
    sa.Column('janium_campaign_description', sa.String(length=512), nullable=True),
    sa.Column('is_messenger', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_reply_in_email_thread', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('queue_start_time', sa.DateTime(), nullable=False),
    sa.Column('queue_end_time', sa.DateTime(), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.Column('effective_start_date', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('effective_end_date', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['email_config_id'], ['email_config.email_config_id'], ),
    sa.ForeignKeyConstraint(['ulinc_config_id'], ['ulinc_config.ulinc_config_id'], ),
    sa.PrimaryKeyConstraint('janium_campaign_id')
    )
    op.create_table('janium_campaign_step',
    sa.Column('janium_campaign_step_id', sa.String(length=36), nullable=False),
    sa.Column('janium_campaign_id', sa.String(length=36), nullable=False),
    sa.Column('janium_campaign_step_type_id', sa.Integer(), nullable=False),
    sa.Column('janium_campaign_step_delay', sa.Integer(), nullable=False),
    sa.Column('janium_campaign_step_body', sa.Text(), nullable=True),
    sa.Column('janium_campaign_step_subject', sa.String(length=1000), nullable=True),
    sa.Column('queue_start_time', sa.DateTime(), nullable=False),
    sa.Column('queue_end_time', sa.DateTime(), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.Column('effective_start_date', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('effective_end_date', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['janium_campaign_id'], ['janium_campaign.janium_campaign_id'], ),
    sa.ForeignKeyConstraint(['janium_campaign_step_type_id'], ['janium_campaign_step_type.janium_campaign_step_type_id'], ),
    sa.PrimaryKeyConstraint('janium_campaign_step_id')
    )
    op.create_table('ulinc_campaign',
    sa.Column('ulinc_campaign_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_config_id', sa.String(length=36), nullable=False),
    sa.Column('janium_campaign_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_campaign_name', sa.String(length=512), nullable=False),
    sa.Column('ulinc_is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('ulinc_ulinc_campaign_id', sa.String(length=16), nullable=False),
    sa.Column('ulinc_is_messenger', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['janium_campaign_id'], ['janium_campaign.janium_campaign_id'], ),
    sa.ForeignKeyConstraint(['ulinc_config_id'], ['ulinc_config.ulinc_config_id'], ),
    sa.PrimaryKeyConstraint('ulinc_campaign_id')
    )
    op.create_table('contact',
    sa.Column('contact_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_campaign_id', sa.String(length=36), nullable=False),
    sa.Column('contact_source_id', sa.String(length=36), nullable=False),
    sa.Column('ulinc_id', sa.String(length=16), nullable=False),
    sa.Column('ulinc_ulinc_campaign_id', sa.String(length=16), nullable=False),
    sa.Column('tib_id', sa.String(length=36), nullable=True),
    sa.Column('contact_info', sa.JSON(), nullable=False),
    sa.Column('asOfStartTime', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.Column('asOfEndTime', sa.DateTime(), server_default=sa.text('(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))'), nullable=True),
    sa.ForeignKeyConstraint(['contact_source_id'], ['contact_source.contact_source_id'], ),
    sa.ForeignKeyConstraint(['ulinc_campaign_id'], ['ulinc_campaign.ulinc_campaign_id'], ),
    sa.PrimaryKeyConstraint('contact_id')
    )
    op.create_table('action',
    sa.Column('action_id', sa.String(length=36), nullable=False),
    sa.Column('contact_id', sa.String(length=36), nullable=False),
    sa.Column('action_type_id', sa.Integer(), nullable=False),
    sa.Column('action_timestamp', sa.DateTime(), nullable=True),
    sa.Column('action_message', sa.Text(), nullable=True),
    sa.Column('to_email_addr', sa.String(length=64), nullable=True),
    sa.Column('email_message_id', sa.String(length=512), nullable=True),
    sa.Column('date_added', sa.DateTime(), server_default=sa.text('(UTC_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['action_type_id'], ['action_type.action_type_id'], ),
    sa.ForeignKeyConstraint(['contact_id'], ['contact.contact_id'], ),
    sa.PrimaryKeyConstraint('action_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('action')
    op.drop_table('contact')
    op.drop_table('ulinc_campaign')
    op.drop_table('janium_campaign_step')
    op.drop_table('janium_campaign')
    op.drop_table('contact_source')
    op.drop_table('ulinc_config')
    op.drop_table('email_config')
    op.drop_table('account')
    op.drop_table('user')
    op.drop_table('cookie')
    op.drop_table('time_zone')
    op.drop_table('janium_campaign_step_type')
    op.drop_table('email_server')
    op.drop_table('dte')
    op.drop_table('credentials')
    op.drop_table('cookie_type')
    op.drop_table('contact_source_type')
    op.drop_table('action_type')
    # ### end Alembic commands ###
