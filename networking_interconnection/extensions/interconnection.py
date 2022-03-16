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
import abc

import six

from neutron.api.v2 import resource_helper
from neutron_lib.api.definitions import bgpvpn as api_bgpvpn_def
from neutron_lib.api import extensions as api_extensions
from neutron_lib.db import constants as db_const
from neutron_lib import exceptions as n_exc
from neutron_lib.services import base as libbase

from oslo_log import log

from networking_interconnection._i18n import _
from networking_interconnection.common import constants

LOG = log.getLogger(__name__)
ALIAS = "interconnection"


class NotFound(n_exc.NotFound):
    message = _("Interconnection %(id)s could not be found")


class ResourceNotFound(n_exc.BadRequest):
    message = _("Resource %(resource_type)s with ID "
                "%(remote_resource_id)s not found.")


class RemoteKeystoneUnavailable(n_exc.BadRequest):
    message = _("Remote keystone %(remote_keystone)s unavailable.")


class ProjectOrDomainNotFound(n_exc.BadRequest):
    message = _("Project or domain with ID %(project_id)s not found.")


class ResourcesOwnedByDifferentDomains(n_exc.BadRequest):
    message = _("local_resource_id and remote_resource_id owned by different"
                " domains")


class InterconnectionOwnedByDifferentDomains(n_exc.BadRequest):
    message = _("interconnections %(local)s and %(remote)s owned by different"
                " domains")


class RegionConflict(n_exc.BadRequest):
    message = _("Remote region %(remote_region)s cannot match with local "
                "region %(local_region)s.")


class BgpvpnUsedByAnotherInterconnaction(n_exc.Conflict):
    message = _("BGPVPN %(bgpvpn)s already used with %(interconnection)s. "
                "the driver does not support same bgpvpn associated to "
                "multiple bgpvpns.")


class BgpvpnExportTargetsIsEpmty(n_exc.BadRequest):
    message = _("BGPVPN %(bgpvpn)s has not export targets, nothing to use for"
                " interconnection")


class InvalidRemoteInterconnection(n_exc.BadRequest):
    message = _("Remote interconnection invalid.")


class DriverError(n_exc.NeutronException):
    message = _("%(method)s failed.")


RESOURCE_ATTRIBUTE_MAP = {
    constants.API_COLLECTION_NAME: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True,
               'enforce_policy': True},
        # policy supports only legacy tenant_id field
        'tenant_id': {'allow_post': True, 'allow_put': False,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True,
                      'enforce_policy': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'is_visible': True},
        'type': {'allow_post': True, 'allow_put': False,
                 'default': constants.TYPE_BGPVPN,
                 'validate': {'type:values': constants.TYPES},
                 'is_visible': True},
        'state': {'allow_post': False, 'allow_put': True,
                  'default': constants.STATE_WAITING,
                  'validate': {'type:values': constants.STATES},
                  'is_filter': True,
                  'is_visible': True,
                  'enforce_policy': True},
        'local_resource_id': {'allow_post': True, 'allow_put': False,
                              'validate': {'type:uuid': None},
                              'is_filter': True,
                              'is_visible': True,
                              'enforce_policy': True},
        'remote_resource_id': {'allow_post': True, 'allow_put': False,
                               'validate': {'type:uuid': None},
                               'is_filter': True,
                               'is_visible': True,
                               'enforce_policy': True},
        'remote_region': {'allow_post': True, 'allow_put': False,
                          'validate': {'type:not_empty_string': 255},
                          'is_filter': True,
                          'is_visible': True,
                          'enforce_policy': True},
        'remote_interconnection_id': {'allow_post': True, 'allow_put': True,
                                      'default': None,
                                      'validate': {'type:uuid_or_none': None},
                                      'is_filter': True,
                                      'is_visible': True,
                                      'enforce_policy': True},
        'local_parameters': {'allow_post': False, 'allow_put': False,
                             'validate': {'type:dict': None},
                             'is_visible': True},
        'remote_parameters': {'allow_post': False, 'allow_put': False,
                              'validate': {'type:dict': None},
                              'is_visible': True},
    }
}


class Interconnection(api_extensions.ExtensionDescriptor):

    @classmethod
    def get_name(cls):
        return "Neutron networking interconnection extension"

    @classmethod
    def get_alias(cls):
        return ALIAS

    @classmethod
    def get_description(cls):
        return ("API extension for networking interconnection service plugin"
                " provides functionality to manage cross-region network "
                "connections based on BGPVPNs.")

    @classmethod
    def get_updated(cls):
        return "2021-10-25T15:30:44-00:00"

    @classmethod
    def get_resources(cls):
        plural_mappings = resource_helper.build_plural_mappings(
            {}, RESOURCE_ATTRIBUTE_MAP)
        return resource_helper.build_resource_info(
            plural_mappings,
            RESOURCE_ATTRIBUTE_MAP,
            ALIAS,
            # register_quota=True,
            # translate_name=True,
        )

    @classmethod
    def get_plugin_interface(cls):
        return InterconnectionPluginBase

    @classmethod
    def get_required_extensions(cls):
        return [api_bgpvpn_def.ALIAS]


@six.add_metaclass(abc.ABCMeta)
class InterconnectionPluginBase(libbase.ServicePluginBase):

    path_prefix = "/" + ALIAS
    supported_extension_aliases = [
        ALIAS,
    ]

    def get_plugin_name(self):
        return ALIAS + '_svc_plugin'

    def get_plugin_type(self):
        return ALIAS

    def get_plugin_description(self):
        return 'BGP VPN Interconnection service plugin'

    @abc.abstractmethod
    def create_interconnection(self, context, interconnection):
        pass

    @abc.abstractmethod
    def get_interconnections(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_interconnection(self, context, id, fields=None):
        pass

    @abc.abstractmethod
    def update_interconnection(self, context, id, interconnection):
        pass

    @abc.abstractmethod
    def delete_interconnection(self, context, id):
        pass
