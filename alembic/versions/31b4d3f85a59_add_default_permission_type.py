"""add default permission type

Revision ID: 31b4d3f85a59
Revises: 19ad6d22004d
Create Date: 2021-04-14 11:00:11.460966

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
revision = '31b4d3f85a59'
down_revision = '19ad6d22004d'
branch_labels = None
depends_on = None

permission = table('permission',
    column('permission_id', String),
    column('permission_name', String),
    column('permission_description', String),
    column('updated_by', String)
)


def upgrade():
    op.bulk_insert(permission,
        [
            {
                'permission_id':  model.Permission.default_permission_id,
                'permission_name': 'Default Permission',
                'permission_description': 'Because whatever',
                'updated_by': model.User.system_user_id
            }
        ]
    )

def downgrade():
    pass
