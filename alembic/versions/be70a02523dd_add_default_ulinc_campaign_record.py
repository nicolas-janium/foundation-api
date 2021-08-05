"""add default ulinc_campaign record

Revision ID: be70a02523dd
Revises: ec63aa69a28a
Create Date: 2021-08-05 14:17:07.182022

"""
import json
import os
import uuid

import sqlalchemy as sa
from alembic import op
from foundation_api.V1.sa_db import model
from sqlalchemy import (JSON, Boolean, Column, Computed, DateTime, ForeignKey,
                        Integer, PrimaryKeyConstraint, String, Table, Text,
                        create_engine, engine)
from sqlalchemy.sql import column, false, func, null, table, text, true



# revision identifiers, used by Alembic.
revision = 'be70a02523dd'
down_revision = 'ec63aa69a28a'
branch_labels = None
depends_on = None

ulinc_campaign = table('ulinc_campaign',
    column('ulinc_campaign_id', String),
    column('ulinc_config_id', String),
    column('janium_campaign_id', String),
    column('ulinc_campaign_name', String),
    column('ulinc_is_active', Boolean),
    column('ulinc_is_messenger', Boolean),
    column('ulinc_ulinc_campaign_id', String),
    column('connection_request_message', String),
    column('messenger_origin_message', String)
)

def upgrade():
    op.execute(
        ulinc_campaign.insert().values(
            ulinc_campaign_id=model.Ulinc_campaign.unassigned_ulinc_campaign_id,
            ulinc_config_id=model.Ulinc_config.unassigned_ulinc_config_id,
            janium_campaign_id=model.Janium_campaign.unassigned_janium_campaign_id,
            ulinc_campaign_name='Unassigned Ulinc Campaign',
            ulinc_is_messenger=False,
            ulinc_is_active=False,
            ulinc_ulinc_campaign_id='9999',
            connection_request_message=None,
            messenger_origin_message=None
        )
    )


def downgrade():
    pass
