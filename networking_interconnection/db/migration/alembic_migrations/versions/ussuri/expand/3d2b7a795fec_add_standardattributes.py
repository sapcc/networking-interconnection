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

"""add standardattributes

Revision ID: 3d2b7a795fec
Revises: 8c912716f498
Create Date: 2021-12-02 19:52:22.987529

"""

from alembic import op
from datetime import datetime
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3d2b7a795fec'
down_revision = '8c912716f498'

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
    # this commit is necessary to allow further operations
    session.commit()
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
