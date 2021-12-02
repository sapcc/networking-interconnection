# Copyright (c) 2021 Cloudification GmbH.
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

Revision ID: 01fc82e5c934
Create Date: 2021-10-25 15:30:44.004130

"""

from alembic import op
import sqlalchemy as sa

from neutron.db.migration import cli

from networking_interconnection.common import constants

# revision identifiers, used by Alembic.
revision = '01fc82e5c934'
down_revision = 'start_networking_interconnection'
branch_labels = (cli.CONTRACT_BRANCH,)

states = sa.Enum(*constants.STATES, name="states")
types = sa.Enum(*constants.TYPES, name="types")


def upgrade():
    op.create_table(
        'interconnections',
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
