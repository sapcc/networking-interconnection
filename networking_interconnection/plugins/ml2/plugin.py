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
from neutron_lib.callbacks import events
from neutron_lib.callbacks import registry

from keystoneauth1.exceptions import http as k_exc
from neutronclient.common import exceptions as n_client_exc
from oslo_config import cfg
from oslo_log import log

from networking_interconnection.common import clients
from networking_interconnection.common import constants
from networking_interconnection.db import interconnaction_db as intc_db
from networking_interconnection.extensions import interconnection as intc_exc
from networking_interconnection.neutronclient.osc.v2 import (
    interconnection as osc_v2)
from networking_interconnection import opts

LOG = log.getLogger(__name__)
CONF = cfg.CONF


@registry.has_registry_receivers
class InterconnectionPlugin(intc_exc.InterconnectionPluginBase,
                            intc_db.InterconnectionPluginDb):

    def __init__(self):
        super(InterconnectionPlugin, self).__init__()

        # Register config options
        opts.register_interconnection_options(CONF)

        # Save config
        self.cfg = CONF.interconnection

        self.mngr = clients.ClientManager(CONF.interconnection)

        self.db = intc_db.InterconnectionPluginDb()

    def create_interconnection(self, context, interconnection):
        data = interconnection[constants.API_RESOURCE_NAME]
        if not data['remote_interconnection_id']:
            data['state'] = constants.STATE_WAITING
        else:
            data['state'] = constants.STATE_VALIDATING
        if not self.cfg.allow_regions_coincidence:
            self._validate_regions(data)
        remote_neutron, remote_keystone = self.mngr.get_clients(
            data['remote_region'])
        local_neutron, local_keystone = self.mngr.get_clients(
            self.cfg.region_name)
        local, remote = self._validate_resources(
            data, remote_neutron, remote_keystone, local_neutron,
            local_keystone)
        self._validate_remote_interconnection(
            data, remote_neutron, remote_keystone, local_keystone)
        data['local_parameters'] = self._get_parameters(local)
        data['remote_parameters'] = self._get_parameters(remote)
        db_obj = self.db.create_interconnection(context, data)
        # Neutron Callback System the only one way how we can start validating
        # interconnection in background. This notification will be catch by
        # _validating_interconnection function.
        registry.publish(
            constants.INVTERCONNECTION_RESOURCE,
            events.AFTER_CREATE, self,
            payload=events.DBEventPayload(
                context,
                metadata={
                    "interconnection": db_obj,
                    "local_resource": local,
                    "remote_resource": remote,
                    "remote_neutron": remote_neutron,
                    "local_neutron": local_neutron,
                }
            )
        )
        return db_obj

    def get_interconnections(self, context, filters=None, fields=None):
        return self.db.get_interconnections(context, filters, fields)

    def get_interconnection(self, context, id, fields=None):
        return self.db.get_interconnection(context, id, fields)

    def update_interconnection(self, context, id, interconnection):
        data = interconnection[constants.API_RESOURCE_NAME]
        db_obj = self.db.update_interconnection(context, id, data)
        # if state was changed to VALIDATED we have to synchronize resources
        if data.get('state') and data['state'] == constants.STATE_VALIDATED:
            # Neutron Callback System the only one way how we can start
            # synchronization in background.
            registry.publish(
                constants.INVTERCONNECTION_RESOURCE,
                events.AFTER_UPDATE, self,
                payload=events.DBEventPayload(
                    context,
                    metadata={
                        "interconnection": db_obj,
                    }
                )
            )
        return db_obj

    def delete_interconnection(self, context, id):
        db_obj = self.db.delete_interconnection(context, id)
        # Neutron Callback System the only one way how we can start
        # synchronization in background.
        registry.publish(
            constants.INVTERCONNECTION_RESOURCE,
            events.AFTER_DELETE, self,
            payload=events.DBEventPayload(
                context,
                metadata={
                    "interconnection": db_obj,
                }
            )
        )
        return db_obj

    @registry.receives(
        constants.INVTERCONNECTION_RESOURCE, [events.AFTER_CREATE])
    def _sync_interconnections(self, resource, event, trigger, payload):
        intcn = payload.metadata.get('interconnection')
        local_neutron = payload.metadata.get('local_neutron')
        remote_neutron = payload.metadata.get('remote_neutron')
        # nothing to validate if remote interconection is not ready
        if not intcn['remote_interconnection_id']:
            return
        # set state VALIDATED for each side to start resources synchronization
        # see _sync_resources function. We have to update local interconnection
        # via API instead of database because we need to start background
        # action for AFTER_UPDATE event on each side in the same way.
        self._update_interconnection(
            remote_neutron, intcn['remote_interconnection_id'],
            state=constants.STATE_VALIDATED,
            remote_interconnection_id=intcn['id'])
        self._update_interconnection(
            local_neutron, intcn['id'],
            state=constants.STATE_VALIDATED)

    @registry.receives(
        constants.INVTERCONNECTION_RESOURCE, [events.AFTER_UPDATE,
                                              events.AFTER_DELETE])
    def _sync_resources(self, resource, event, trigger, payload):
        intcn = payload.metadata.get('interconnection')
        context = payload.context
        try:
            # get local and remote clients
            local_neutron, _ = self.mngr.get_clients(self.cfg.region_name)
            remote_neutron, _ = self.mngr.get_clients(intcn['remote_region'])
            # get local and remote resources
            remote_res = self._get_bgpvpn(
                remote_neutron, intcn['remote_resource_id'])
            local_res = self._get_bgpvpn(
                local_neutron, intcn['local_resource_id'])
            if event == events.AFTER_UPDATE:
                # import/export targets synchronization
                imports = set(
                    local_res['import_targets'] + remote_res['export_targets'])
                local_neutron.update_bgpvpn(
                    intcn['local_resource_id'],
                    body={'bgpvpn': {'import_targets': list(imports)}})
                # update interconnection to ACTIVE
                self.db.update_interconnection(
                    context, intcn['id'], {'state': constants.STATE_ACTIVE})
            if event == events.AFTER_DELETE:
                # import/export targets synchronization
                imports = set(
                    local_res['import_targets']) - set(
                        remote_res['export_targets'])
                local_neutron.update_bgpvpn(
                    intcn['local_resource_id'],
                    body={'bgpvpn': {'import_targets': list(imports)}})
        except n_client_exc.NeutronClientException as err:
            LOG.error('Could not synchronize targets for local resource bgpvpn'
                      ' with ID %s. Details: request_ids=%s msg=%s'
                      % (intcn['local_resource_id'], err.request_ids, err))
            if event != events.AFTER_DELETE:
                self.db.update_interconnection(
                    context, intcn['id'],
                    {'state': constants.STATE_TEARDOWN})

    def _update_interconnection(self, client, id, **kwargs):
        client.put(
            osc_v2.PATH_SINGLE + id,
            body={constants.API_RESOURCE_NAME: kwargs})

    def _validate_resources(self, data, remote_neutron, remote_keystone,
                            local_neutron, local_keystone):
        # get local and remote resources
        remote_res = self._get_bgpvpn(
            remote_neutron, data['remote_resource_id'])
        local_res = self._get_bgpvpn(local_neutron, data['local_resource_id'])
        # validate owner of resources
        remote_domain_name = self._get_domain_name(
            remote_keystone, remote_res['project_id'])
        local_domain_name = self._get_domain_name(
            local_keystone, local_res['project_id'])
        if remote_domain_name != local_domain_name:
            raise intc_exc.ResourcesOwnedByDifferentDomains()
        # validate targets
        if not remote_res['export_targets']:
            raise intc_exc.BgpvpnExportTargetsIsEpmty(bgpvpn=remote_res['id'])
        if not local_res['export_targets']:
            raise intc_exc.BgpvpnExportTargetsIsEpmty(bgpvpn=local_res['id'])
        return local_res, remote_res

    def _validate_remote_interconnection(self, data, remote_neutron,
                                         remote_keystone, local_keystone):
        if not data['remote_interconnection_id']:
            return
        # get remote interconnection
        r_intcn = remote_neutron.get(
            osc_v2.PATH_SINGLE + data['remote_interconnection_id']
        )[constants.API_RESOURCE_NAME]
        # check owner of remote interconnection
        remote_domain_name = self._get_domain_name(
            remote_keystone, r_intcn['project_id'])
        local_domain_name = self._get_domain_name(
            local_keystone, data['project_id'])
        if remote_domain_name != local_domain_name:
            raise intc_exc.InterconnectionOwnedByDifferentDomains(
                local=data['project_id'], remote=r_intcn['project_id'])
        # update remote interconnection to set state VALIDATING and remote
        # interconnection ID
        self._update_interconnection(
            remote_neutron, data['remote_interconnection_id'],
            state=constants.STATE_VALIDATING)
        # check local and remote resources
        if (r_intcn['remote_resource_id'] != data['local_resource_id']
                or r_intcn['local_resource_id'] != data['remote_resource_id']):
            LOG.error('Invalid resource settings in remote interconnection %s.'
                      % (data['remote_interconnection_id']))
            raise intc_exc.InvalidRemoteInterconnection()

    def _validate_regions(self, data):
        if data['remote_region'] == self.cfg.region_name:
            raise intc_exc.RegionConflict(
                remote_region=data['remote_region'],
                local_region=self.cfg.region_name)

    def _get_parameters(self, bgpvpn):
        params_to_copy = ['project_id']
        params = {}
        for key, val in bgpvpn.items():
            if key in params_to_copy and val:
                # all values in parameters should be a list for pretty format
                params[key] = [val] if not isinstance(val, list) else val
        return params

    def _get_bgpvpn(self, neutron_client, bgpvpn_id):
        try:
            return neutron_client.show_bgpvpn(bgpvpn_id)['bgpvpn']
        except n_client_exc.NotFound:
            raise intc_exc.ResourceNotFound(
                resource_type='bgpvpn',
                remote_resource_id=bgpvpn_id)

    def _get_domain_name(self, keystone_client, project_id):
        try:
            project = keystone_client.projects.get(project_id)
            return keystone_client.domains.get(project.domain_id).name
        except k_exc.NotFound:
            raise intc_exc.ProjectOrDomainNotFound(
                project_id=project_id)
