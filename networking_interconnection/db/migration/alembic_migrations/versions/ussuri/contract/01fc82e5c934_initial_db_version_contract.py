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

Revision ID: 01fc82e5c934
Create Date: 2021-10-25 15:30:44.004130

"""

from neutron.db.migration import cli

# revision identifiers, used by Alembic.
revision = '01fc82e5c934'
down_revision = 'cad6e0c73704'
branch_labels = (cli.CONTRACT_BRANCH,)


def upgrade():
    pass
