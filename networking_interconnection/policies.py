# Copyright (c) 2021 Cloudification GmbH.
# All Rights Reserved.
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

from oslo_policy import policy

from neutron.conf.policies import base as common_base


RULE_ADMIN_OR_OWNER = 'rule:admin_or_owner'
RULE_ADMIN_ONLY = 'rule:admin_only'

rules = [
    policy.RuleDefault(
        name='interconnection',
        check_str='role:cloud_network_admin',
        description='Definition of interconnection admin role'
    ),
    policy.DocumentedRuleDefault(
        'create_interconnection',
        RULE_ADMIN_ONLY,
        'Create an interconnection',
        [
            {
                'method': 'POST',
                'path': '/interconnection/interconnections',
            },
        ]
    ),
    policy.DocumentedRuleDefault(
        'update_interconnection',
        RULE_ADMIN_ONLY,
        'Update a BGP VPN',
        [
            {
                'method': 'PUT',
                'path': '/interconnection/interconnections/{id}',
            },
        ]
    ),
    policy.DocumentedRuleDefault(
        'update_interconnection:name',
        RULE_ADMIN_OR_OWNER,
        'Update ``name`` attribute of a interconnection',
        [
            {
                'method': 'PUT',
                'path': '/interconnection/interconnections/{id}',
            },
        ]
    ),
    policy.DocumentedRuleDefault(
        'update_interconnection:state',
        common_base.policy_or(
            RULE_ADMIN_ONLY,
            'rule:interconnection',
        ),        'Update ``state`` attribute of a interconnection',
        [
            {
                'method': 'PUT',
                'path': '/interconnection/interconnections/{id}',
            },
        ]
    ),
    policy.DocumentedRuleDefault(
        'update_interconnection:remote_interconnection_id',
        common_base.policy_or(
            RULE_ADMIN_ONLY,
            'rule:interconnection',
        ),
        'Update ``remote_interconnection_id`` attribute of a interconnection',
        [
            {
                'method': 'PUT',
                'path': '/interconnection/interconnections/{id}',
            },
        ]
    ),
    policy.DocumentedRuleDefault(
        'delete_interconnection',
        RULE_ADMIN_ONLY,
        'Delete an interconnection',
        [
            {
                'method': 'DELETE',
                'path': '/interconnection/interconnections/{id}',
            },
        ]
    ),
    policy.DocumentedRuleDefault(
        'get_interconnection',
        RULE_ADMIN_OR_OWNER,
        'Get interconnections',
        [
            {
                'method': 'GET',
                'path': '/interconnection/interconnections',
            },
            {
                'method': 'GET',
                'path': '/interconnection/interconnections/{id}',
            },
        ]
    ),
]


def list_rules():
    return rules
