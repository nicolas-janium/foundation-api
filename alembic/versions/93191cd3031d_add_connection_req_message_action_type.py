"""add connection req message action type

Revision ID: 93191cd3031d
Revises: 28475d852b78
Create Date: 2021-08-13 11:09:42.373512

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
revision = '93191cd3031d'
down_revision = '28475d852b78'
branch_labels = None
depends_on = None

action_type = table('action_type',
    column('action_type_id', Integer),
    column('action_type_name', String),
    column('action_type_description', String)
)

def upgrade():
    op.bulk_insert(action_type,
        [
            {'action_type_id': 23, 'action_type_name': 'ulinc_connector_origin_message', 'action_type_description': 'This is the origin message for Ulinc Connector Campaigns'}
        ]
    )


def downgrade():
    pass
