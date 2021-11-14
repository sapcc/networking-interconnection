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
from keystoneauth1.session import Session as KeystoneSession
from keystoneclient.auth.identity.v3 import Password as PasswordClient
from keystoneclient.v3.client import Client as KeystoneClient
from neutronclient.neutron.client import Client as NeutronClient
from oslo_log import log

from networking_interconnection.extensions import interconnection as intc_exc
from networking_interconnection import version

LOG = log.getLogger(__name__)


class ClientManager(object):

    def __init__(self, config):
        # Save config
        self.cfg = config
        # Validate local keystone credentials
        self._keystone_session(self.cfg.region_name)

    def _keystone_session(self, region):
        auth_url = self._get_auth_url(region)
        session = KeystoneSession(
            auth=PasswordClient(
                auth_url=auth_url,
                username=self.cfg.username,
                password=self.cfg.password,
                project_name=self.cfg.project_name,
                user_domain_name=self.cfg.user_domain_name,
                project_domain_name=self.cfg.project_domain_name,
            ),
            timeout=self.cfg.keystone_connect_timeout,
            connect_retries=self.cfg.keystone_connect_retries,
            app_name='Neutron Interconnection',
            app_version=version.version_info,
        )
        # Simple check that credentials are correct
        session.get_token()
        return session

    def get_clients(self, region):
        try:
            session = self._keystone_session(region)
            neutron = NeutronClient(
                api_version='2.0',
                session=session,
                region_name=region,
                endpoint_type=self.cfg.endpoint_type,
            )
            keystone = KeystoneClient(
                session=session,
                region_name=region,
                endpoint_type=self.cfg.endpoint_type,
            )
            return neutron, keystone
        except Exception:
            LOG.exception('Could not get clients.')
            raise intc_exc.RemoteKeystoneUnavailable(
                remote_keystone=self._get_auth_url(region))

    def _get_auth_url(self, region):
        return self.cfg.auth_url_template % {'region': region}
