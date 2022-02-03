#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import itertools

from oslo_config import cfg


INTERCONNECTION_CONFIG_OPTS = [
    # Keystone options
    # We cannot use config generator from keystone lib because in our case we
    # have to use names instead of IDs for keystone authentication.
    cfg.StrOpt('network_admin_role',
               default='cloud_network_admin',
               help='The keystone service role that can manage any resources '
                    'in any projects.'),
    cfg.StrOpt('auth_url_template',
               default='https://identity-3.%(region)s.cloud.sap/v3',
               help='Templated keystone auth_url to get remote keystone API, '
                    'should contain %(region)s section.'),
    cfg.StrOpt('endpoint_type',
               default='public',
               help='The keystone auth_url in the current region.'),
    cfg.StrOpt('region_name',
               default='RegionOne',
               help='The current region.'),
    cfg.StrOpt('username',
               default='neutron_interconnection_plugin',
               help='The username of service user with a keystone role that '
                    'can manage network resources in all regions.'),
    cfg.StrOpt('password',
               default=None,
               help='The password of service user with a keystone role that '
                    'can manage network resources in all project.'),
    cfg.StrOpt('project_name',
               default='service',
               help='The service project name of service user with a keystone '
                    'role that can manage network resources in all project.'),
    cfg.StrOpt('user_domain_name',
               default='Default',
               help='The user domain name of service user with a keystone role'
                    ' that can manage network resources in all projects.'),
    cfg.StrOpt('project_domain_name',
               default='Default',
               help='The project domain name of service user with a keystone '
                    'role that can manage network resources in all projects.'),
    cfg.IntOpt('keystone_connect_retries',
               default=5,
               help='Number of connect retries to keystone API endpoint.'),
    cfg.FloatOpt('keystone_connect_timeout',
                 default=10,
                 help='Keystone request timeout in seconds.'),
    cfg.BoolOpt('allow_regions_coincidence',
                default=False,
                help='Allow coincidence of interconnctions\' regions.'),
    cfg.BoolOpt('check_credentials_on_start',
                default=False,
                help='If True Neutron server will try to get keystone token for'
                     ' interconnection plugin on start and raise exceptions if'
                     ' it\'s not working.')
]


def register_interconnection_options(cfg=cfg.CONF):
    cfg.register_opts(INTERCONNECTION_CONFIG_OPTS, group='interconnection')


def list_interconnection_opts():
    return [
        ('interconnection', itertools.chain(INTERCONNECTION_CONFIG_OPTS)),
    ]
