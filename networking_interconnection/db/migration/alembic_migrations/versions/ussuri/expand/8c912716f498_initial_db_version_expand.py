# Copyright (c) 2021 Cloudification, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""Initial db version

Revision ID: 8c912716f498
Create Date: 2021-10-25 15:30:44.004130

"""
from alembic import op
from datetime import datetime
import sqlalchemy as sa

from neutron.db.migration import cli

from networking_interconnection.common import constants

# revision identifiers, used by Alembic.
revision = '8c912716f498'
down_revision = 'cad6e0c73704'
branch_labels = (cli.EXPAND_BRANCH,)

states = sa.Enum(*constants.STATES, name="states")
types = sa.Enum(*constants.TYPES, name="types")

standardattrs = sa.Table(
    'standardattributes', sa.MetaData(),
    sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
    sa.Column('resource_type', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime, default=datetime.now()),
    sa.Column('updated_at', sa.DateTime, default=datetime.now())
)


def upgrade():
    table = 'interconnections'
    op.create_table(
        table,
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('type', types, nullable=False),
        sa.Column('state', states, nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('local_resource_id', sa.String(length=36), nullable=False),
        sa.Column('remote_resource_id', sa.String(length=36), nullable=False),
        sa.Column('remote_region', sa.String(length=255), nullable=False),
        sa.Column('remote_interconnection_id',
                  sa.String(length=36), nullable=True),
        sa.Column('local_parameters', sa.Unicode(length=500), nullable=True),
        sa.Column('remote_parameters', sa.Unicode(length=500), nullable=True),
        sa.Column('standard_attr_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # Add `interconnection` resource to `standardattributes` table
    session = sa.orm.Session(bind=op.get_bind())
    with session.begin(subtransactions=True):
        res = session.execute(
            standardattrs.select().where(
                standardattrs.c.resource_type == op.inline_literal(table)
            )
        ).fetchone()
        if not res:
            session.execute(
                standardattrs.insert().values(resource_type=table))
    # Add unique constraint
    op.create_unique_constraint(
        constraint_name='uniq_%s0standard_attr_id' % table,
        table_name=table, columns=['standard_attr_id'])
    # Add foreign key
    op.create_foreign_key(
        constraint_name=None, source_table=table,
        referent_table='standardattributes',
        local_cols=['standard_attr_id'], remote_cols=['id'],
        ondelete='CASCADE')
