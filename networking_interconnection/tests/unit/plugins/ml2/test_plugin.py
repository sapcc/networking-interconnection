# Copyright (c) 2021 Cloudification GmbH
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

import contextlib
import copy
import mock
import unittest
import webob.exc

from neutron_lib.plugins import directory
from oslo_config import cfg
from oslo_utils import uuidutils

from keystoneauth1.exceptions import http as k_exc
from networking_bgpvpn.neutron import extensions as bgpvpn_ext
from networking_bgpvpn.neutron.services import plugin as bgpvpn_plugin
from neutron.api import extensions as api_extensions
from neutron.db import servicetype_db as sdb
from neutron import extensions as n_extensions
from neutron.tests.unit.db import test_db_base_plugin_v2
from neutron.tests.unit.extensions import test_l3
from neutron.tests.unit.extensions.test_l3 import TestL3NatServicePlugin
from neutron_lib.api.definitions import bgpvpn as bgpvpn_def
from neutronclient.common import exceptions as n_client_exc

from networking_interconnection.common import constants
from networking_interconnection import extensions
from networking_interconnection.extensions import interconnection as intc_exc
from networking_interconnection.plugins.ml2 import plugin

_uuid = uuidutils.generate_uuid


def http_client_error(req, res):
    explanation = "Request '%s %s %s' failed: %s" % (req.method, req.url,
                                                     req.body, res.body)
    return webob.exc.HTTPClientError(code=res.status_int,
                                     explanation=explanation)


class BaseTestCaseMixin(test_db_base_plugin_v2.NeutronDbPluginV2TestCase,
                        test_l3.L3NatTestCaseMixin):

    tenant_id_1 = '4140334e-da3e-4cc8-9331-0fef5e6e30cf'
    tenant_id_2 = 'f35a0457-74ce-4c3b-8909-d724280f338f'

    def setUp(self, core_plugin=None):
        # prepare service provider for bgpvpn plugin
        provider = {
            'service_type': bgpvpn_def.ALIAS,
            'name': 'dummy',
            'driver': ('networking_bgpvpn.neutron.services.service_drivers.'
                       'driver_api.BGPVPNDriverRC'),
            'default': True
        }
        service_providers = (
            mock.patch.object(sdb.ServiceTypeManager,
                              'get_service_providers').start())
        service_providers.return_value = [provider]

        service_plugins = {
            'interconnection_plugin': ('networking_interconnection.plugins.'
                                       'ml2.plugin.InterconnectionPlugin'),
            'bpgpvn_plugin': ('networking_bgpvpn.neutron.services.plugin.'
                              'BGPVPNPlugin'),
            'l3_plugin': ('neutron.tests.unit.extensions.test_l3.'
                          'TestL3NatServicePlugin'),
        }

        extensions_path = ':'.join(extensions.__path__
                                   + n_extensions.__path__
                                   + bgpvpn_ext.__path__)

        client_mngr = mock.patch(
            'networking_interconnection.common.clients.'
            'ClientManager').start().return_value
        client_mngr.get_clients.side_effect = self._mocked_get_clidnets

        self.kc = mock.Mock()
        self.nc_local = mock.Mock()
        self.nc_local.get.side_effect = self._mocked_get
        self.nc_local.put.side_effect = self._mocked_put
        self.nc_local.show_bgpvpn.side_effect = self._mocked_show_bgpvpn
        self.nc_local.update_bgpvpn.side_effect = self._mocked_update_bgpvpn
        self.nc_remote = mock.Mock()
        self.nc_remote.get.side_effect = self._mocked_get
        self.nc_remote.put.side_effect = self._mocked_put
        self.nc_remote.show_bgpvpn.side_effect = self._mocked_show_bgpvpn
        self.nc_remote.update_bgpvpn.side_effect = self._mocked_update_bgpvpn

        # we need to provide a plugin instance, although
        # the extension manager will create a new instance
        # of the plugin
        ext_mgr = api_extensions.PluginAwareExtensionManager(
            extensions_path,
            {intc_exc.ALIAS: plugin.InterconnectionPlugin(),
             bgpvpn_def.ALIAS: bgpvpn_plugin.BGPVPNPlugin(),
             'l3_plugin': TestL3NatServicePlugin()})

        super(BaseTestCaseMixin, self).setUp(
            plugin=core_plugin,
            service_plugins=service_plugins,
            ext_mgr=ext_mgr)

        # find the Interconnection plugin that was instantiated by the
        # extension manager:
        self.intcn_plugin = directory.get_plugin(bgpvpn_def.ALIAS)

        self.bgpvpn_data = {
            'bgpvpn': {
                'name': 'test',
                'type': 'l3',
                'tenant_id': self._tenant_id
            }
        }

        self.intcn_data = {
            'interconnection': {
                'name': 'test',
                'tenant_id': self._tenant_id,
            },
        }

    def _mocked_get_clidnets(self, region):
        if cfg.CONF.interconnection.region_name == region:
            return self.nc_local, self.kc
        else:
            return self.nc_remote, self.kc

    def _set_mocked_functions(self, mock_obj):
        mock_obj.get.side_effect = self._mocked_get
        mock_obj.put.side_effect = self._mocked_put
        mock_obj.show_bgpvpn.side_effect = self._mocked_show_bgpvpn
        mock_obj.update_bgpvpn.side_effect = self._mocked_update_bgpvpn
        return mock_obj

    def _mocked_get(self, path):
        parts = path.strip('/').split('/')
        req = self.new_show_request(
            parts[0] + '/' + parts[1], parts[2])
        res = req.get_response(self.ext_api)
        if res.status_int >= 400:
            raise http_client_error(req, res)
        return self.deserialize('json', res)

    def _mocked_put(self, path, body):
        parts = path.strip('/').split('/')
        req = self.new_update_request(
            parts[0] + '/' + parts[1], body, parts[2])
        res = req.get_response(self.ext_api)
        if res.status_int >= 400:
            raise http_client_error(req, res)

    def _mocked_show_bgpvpn(self, bgpvpn_id):
        return self._mocked_get('/bgpvpn/bgpvpns/%s' % bgpvpn_id)

    def _mocked_update_bgpvpn(self, bgpvpn_id, body):
        return self._mocked_put('/bgpvpn/bgpvpns/%s' % bgpvpn_id, body)

    @contextlib.contextmanager
    def bgpvpn(self, do_delete=True, **kwargs):
        req_data = copy.deepcopy(self.bgpvpn_data)

        fmt = 'json'
        if kwargs.get('data'):
            req_data = kwargs.get('data')
        else:
            req_data['bgpvpn'].update(kwargs)
        req = self.new_create_request(
            'bgpvpn/bgpvpns', req_data, fmt=fmt)
        res = req.get_response(self.ext_api)
        if res.status_int >= 400:
            raise http_client_error(req, res)
        bgpvpn = self.deserialize('json', res)
        yield bgpvpn['bgpvpn']
        if do_delete:
            self._delete('bgpvpn/bgpvpns',
                         bgpvpn['bgpvpn']['id'])

    @contextlib.contextmanager
    def intcnt(self, do_delete=True, **kwargs):
        req_data = copy.deepcopy(self.intcn_data)

        fmt = 'json'
        if kwargs.get('data'):
            req_data = kwargs.get('data')
        else:
            req_data['interconnection'].update(kwargs)
        req = self.new_create_request(
            'interconnection/interconnections', req_data, fmt=fmt)
        res = req.get_response(self.ext_api)
        if res.status_int >= 400:
            raise http_client_error(req, res)
        interconnection = self.deserialize('json', res)
        yield interconnection['interconnection']
        if do_delete:
            self._delete('interconnection/interconnections',
                         interconnection['interconnection']['id'])

    def list(self, resource):
        req = self.new_list_request('%s/%ss' % (resource, resource))
        res = req.get_response(self.ext_api)
        return self.deserialize('json', res)['%ss' % resource]


class TestInterconnectionPlugin(BaseTestCaseMixin):

    def test_create_and_delete_interconnections(self):
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with self.intcnt(tenant_id=self.tenant_id_1,
                             local_resource_id=bgpvpn_1['id'],
                             remote_resource_id=bgpvpn_2['id'],
                             remote_region='RegionTwo') as intcn_1:
                # check state of first side
                self.assertEqual(
                    intcn_1['state'], constants.STATE_WAITING)
                # create second side in another region
                cfg.CONF.set_override(
                    'region_name', 'RegionTwo', 'interconnection')
                with self.intcnt(tenant_id=self.tenant_id_2,
                                 local_resource_id=bgpvpn_2['id'],
                                 remote_resource_id=bgpvpn_1['id'],
                                 remote_region='RegionOne',
                                 remote_interconnection_id=intcn_1['id']):
                    # check that interconnections' statuses are valid and
                    # remote_interconnection_ids were updated
                    for el in self.list('interconnection'):
                        self.assertEqual(el['state'], constants.STATE_ACTIVE)
                        self.assertIsNotNone(el['remote_interconnection_id'])
                        self.assertIn('project_id', el['local_parameters'])
                        self.assertIn('project_id', el['remote_parameters'])
                    # check that import-targets were updated on both sides
                    for el in self.list('bgpvpn'):
                        self.assertEqual(sorted(['6000:1', '5000:1']),
                                        sorted(el['import_targets']))

            # check that import-targets were reverted on both sides
            for el in self.list('bgpvpn'):
                self.assertEqual(1, len(el['import_targets']))

    def test__sync_resources_neutron_failed(self):
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with self.intcnt(tenant_id=self.tenant_id_1,
                             local_resource_id=bgpvpn_1['id'],
                             remote_resource_id=bgpvpn_2['id'],
                             remote_region='RegionTwo') as intcn_1:
                # check state of first side
                self.assertEqual(
                    intcn_1['state'], constants.STATE_WAITING)
                # create second side in another region
                cfg.CONF.set_override(
                    'region_name', 'RegionTwo', 'interconnection')
                self.nc_local.update_bgpvpn.side_effect = \
                    n_client_exc.NeutronClientException('some-problem')
                with self.intcnt(tenant_id=self.tenant_id_2,
                                 local_resource_id=bgpvpn_2['id'],
                                 remote_resource_id=bgpvpn_1['id'],
                                 remote_region='RegionOne',
                                 remote_interconnection_id=intcn_1['id']):
                    for el in self.list('interconnection'):
                        self.assertEqual(el['state'], constants.STATE_TEARDOWN)

    def test_create_with_resource_different_domains(self):
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            self.kc.domains.get.side_effect = [
                mock.Mock(),
                mock.Mock(),
            ]
            # create first side
            with unittest.TestCase.assertRaises(
                    self, webob.exc.HTTPClientError) as context:
                with self.intcnt(tenant_id=self.tenant_id_1,
                                 local_resource_id=bgpvpn_1['id'],
                                 remote_resource_id=bgpvpn_2['id'],
                                 remote_region='RegionTwo'):
                    pass
            self.assertIn('owned by different domains', str(context.exception))

    def test_create_with_interconnection_different_domains(self):
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with self.intcnt(tenant_id=self.tenant_id_1,
                             local_resource_id=bgpvpn_1['id'],
                             remote_resource_id=bgpvpn_2['id'],
                             remote_region='RegionTwo') as intcn_1:
                # first two calls should be the same
                domain_mock = mock.Mock()
                self.kc.domains.get.side_effect = [
                    domain_mock,
                    domain_mock,
                    mock.Mock(),
                    mock.Mock(),
                ]
                # create second side in another region
                cfg.CONF.set_override(
                    'region_name', 'RegionTwo', 'interconnection')
                with unittest.TestCase.assertRaises(
                        self, webob.exc.HTTPClientError) as context:
                    # create second side with confused bgpvpns
                    with self.intcnt(tenant_id=self.tenant_id_2,
                                     local_resource_id=bgpvpn_1['id'],
                                     remote_resource_id=bgpvpn_2['id'],
                                     remote_region='RegionOne',
                                     remote_interconnection_id=intcn_1['id']):
                        pass
                self.assertIn(
                    'owned by different domains', str(context.exception))

    def test_create_with_local_region(self):
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with unittest.TestCase.assertRaises(
                    self, webob.exc.HTTPClientError) as context:
                with self.intcnt(tenant_id=self.tenant_id_1,
                                local_resource_id=bgpvpn_1['id'],
                                remote_resource_id=bgpvpn_2['id'],
                                remote_region='RegionOne'):
                    pass
            self.assertIn(
                'cannot match with local region', str(context.exception))

    def test_create_with_non_exist_bgpvpn(self):
        fake = '2308bc7d-88e8-440f-91ac-c68a2729cf5f'
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1:
            with unittest.TestCase.assertRaises(
                    self, webob.exc.HTTPClientError) as context:
                with self.intcnt(tenant_id=self.tenant_id_1,
                                local_resource_id=bgpvpn_1['id'],
                                remote_resource_id=fake,
                                remote_region='RegionTwo'):
                    pass
            self.assertIn(
                'could not be found', str(context.exception))

    def test_create_with_non_exist_domain(self):
        self.kc.domains.get.side_effect = k_exc.NotFound('some-err')
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            with unittest.TestCase.assertRaises(
                    self, webob.exc.HTTPClientError) as context:
                with self.intcnt(tenant_id=self.tenant_id_1,
                                local_resource_id=bgpvpn_1['id'],
                                remote_resource_id=bgpvpn_2['id'],
                                remote_region='RegionTwo'):
                    pass
            self.assertIn(
                'not found', str(context.exception))

    def test_create_with_different_resources_ids(self):
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with self.intcnt(tenant_id=self.tenant_id_1,
                             local_resource_id=bgpvpn_1['id'],
                             remote_resource_id=bgpvpn_2['id'],
                             remote_region='RegionTwo') as intcn_1:
                # create second side in another region
                cfg.CONF.set_override(
                    'region_name', 'RegionTwo', 'interconnection')
                with unittest.TestCase.assertRaises(
                        self, webob.exc.HTTPClientError) as context:
                    with self.intcnt(tenant_id=self.tenant_id_2,
                                     local_resource_id=bgpvpn_1['id'],
                                     remote_resource_id=bgpvpn_2['id'],
                                     remote_region='RegionOne',
                                     remote_interconnection_id=intcn_1['id']):
                        pass
                self.assertIn(
                    'Remote interconnection invalid', str(context.exception))

    def test_create_with_empty_export_targets(self):
        # check first bgpvpn with empty targets
        with self.bgpvpn(import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(export_targets=['6000:1'],
                            import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with unittest.TestCase.assertRaises(
                    self, webob.exc.HTTPClientError) as context:
                with self.intcnt(tenant_id=self.tenant_id_1,
                                 local_resource_id=bgpvpn_1['id'],
                                 remote_resource_id=bgpvpn_2['id'],
                                 remote_region='RegionTwo'):
                    pass
            self.assertIn('has not export targets', str(context.exception))
        # check second bgpvpn with empty targets
        with self.bgpvpn(export_targets=['5000:1'],
                         import_targets=['5000:1'],
                         tenant_id=self.tenant_id_1) as bgpvpn_1, \
                self.bgpvpn(import_targets=['6000:1'],
                            tenant_id=self.tenant_id_2) as bgpvpn_2:
            # create first side
            with unittest.TestCase.assertRaises(
                    self, webob.exc.HTTPClientError) as context:
                with self.intcnt(tenant_id=self.tenant_id_1,
                                 local_resource_id=bgpvpn_1['id'],
                                 remote_resource_id=bgpvpn_2['id'],
                                 remote_region='RegionTwo'):
                    pass
            self.assertIn('has not export targets', str(context.exception))
