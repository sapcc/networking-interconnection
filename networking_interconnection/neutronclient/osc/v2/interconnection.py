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
import logging

from osc_lib.cli import format_columns
from osc_lib.cli.parseractions import KeyValueAction
from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils as osc_utils
from osc_lib.utils import columns as column_util

from neutronclient._i18n import _
from neutronclient.osc import utils as nc_osc_utils

from networking_interconnection.common import constants

LOG = logging.getLogger(__name__)
PATH_SINGLE = '/%s/%s/' % (constants.API_RESOURCE_NAME,
                           constants.API_COLLECTION_NAME)
PATH_COLLECTION = '/%s/%s' % (constants.API_RESOURCE_NAME,
                              constants.API_COLLECTION_NAME)

_attr_map = (
    ('id', 'ID', column_util.LIST_BOTH),
    ('tenant_id', 'Project', column_util.LIST_LONG_ONLY),
    ('project_id', 'Project', column_util.LIST_LONG_ONLY),
    ('name', 'Name', column_util.LIST_BOTH),
    ('type', 'Type', column_util.LIST_LONG_ONLY),
    ('state', 'State', column_util.LIST_BOTH),
    ('local_resource_id', 'Local Resource ID', column_util.LIST_BOTH),
    ('remote_resource_id', 'Remote Resource ID', column_util.LIST_BOTH),
    ('remote_region', 'Remote Region', column_util.LIST_BOTH),
    ('remote_interconnection_id', 'Remote Interconnection ID',
     column_util.LIST_BOTH),
    ('local_parameters', 'Local Parameters', column_util.LIST_LONG_ONLY),
    ('remote_parameters', 'Remote Parameters', column_util.LIST_LONG_ONLY),
)
_formatters = {
    'local_parameters': format_columns.DictListColumn,
    'remote_parameters': format_columns.DictListColumn,
}


class CreateInterconnection(command.ShowOne):
    _description = _("Create Interconnection resource")

    def get_parser(self, prog_name):
        parser = super(CreateInterconnection, self).get_parser(prog_name)
        nc_osc_utils.add_project_owner_option_to_parser(parser)
        parser.add_argument(
            '--name',
            metavar="<name>",
            help=_("Name of the Interconnection"),
        )
        parser.add_argument(
            '--type',
            default=constants.TYPE_BGPVPN,
            choices=constants.TYPES,
            help=(_("Interconnection type of resource (default: %s)")
                  % constants.TYPE_BGPVPN),
        )
        parser.add_argument(
            '--local-resource-id',
            dest='local_resource_id',
            metavar="<local-resource-id>",
            help=_("ID of local resource"),
            required=True,
        )
        parser.add_argument(
            '--remote-resource-id',
            dest='remote_resource_id',
            metavar="<remote-resource-id>",
            help=_("ID of remote resource"),
            required=True,
        )
        parser.add_argument(
            '--remote-region',
            dest='remote_region',
            metavar="<remote-region>",
            help=_("The name of remote region"),
            required=True,
        )
        parser.add_argument(
            '--remote-interconnection-id',
            dest='remote_interconnection_id',
            metavar="<remote-interconnection-id>",
            help=_("ID of remote interconnection"),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        attrs = {}
        if parsed_args.name is not None:
            attrs['name'] = str(parsed_args.name)
        if parsed_args.type is not None:
            attrs['type'] = parsed_args.type
        if parsed_args.local_resource_id is not None:
            attrs['local_resource_id'] = parsed_args.local_resource_id
        if parsed_args.remote_resource_id is not None:
            attrs['remote_resource_id'] = parsed_args.remote_resource_id
        if parsed_args.remote_region is not None:
            attrs['remote_region'] = parsed_args.remote_region
        if parsed_args.remote_interconnection_id is not None:
            attrs['remote_interconnection_id'] = \
                parsed_args.remote_interconnection_id
        if 'project' in parsed_args and parsed_args.project is not None:
            project_id = nc_osc_utils.find_project(
                self.app.client_manager.identity,
                parsed_args.project,
                parsed_args.project_domain,
            ).id
            attrs['project_id'] = project_id
        body = {constants.API_RESOURCE_NAME: attrs}
        obj = client.post(PATH_COLLECTION,
                          body=body)[constants.API_RESOURCE_NAME]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns,
                                             formatters=_formatters)
        return display_columns, data


class SetInterconnection(command.Command):
    _description = _("Set Interconnection properties")

    def get_parser(self, prog_name):
        parser = super(SetInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            'interconnection',
            metavar="<interconnection>",
            help=_("Interconnection to update (name or ID)"),
        )
        parser.add_argument(
            '--name',
            metavar="<name>",
            help=_("Name of the Interconnection"),
        )
        parser.add_argument(
            '--state',
            choices=constants.STATES,
            metavar="<state>",
            help=_("State of the Interconnection"),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        # this is workaround that we have to do to avoid patching of original
        # neutronclient
        setattr(client, 'list_interconnections', self._list)
        attrs = {}
        if parsed_args.name is not None:
            attrs['name'] = str(parsed_args.name)
        if parsed_args.state is not None:
            attrs['state'] = str(parsed_args.state)
        id = client.find_resource(constants.API_RESOURCE_NAME,
                                  parsed_args.interconnection)['id']
        body = {constants.API_RESOURCE_NAME: attrs}
        client.put(PATH_SINGLE + id, body=body)

    def _list(self, retrieve_all=True, **_params):
        client = self.app.client_manager.neutronclient
        return client.list(constants.API_COLLECTION_NAME, PATH_COLLECTION,
                           retrieve_all=retrieve_all, **_params)


class DeleteInterconnection(command.Command):
    _description = _("Delete Interconnection resource(s)")

    def get_parser(self, prog_name):
        parser = super(DeleteInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            'interconnections',
            metavar="<interconnection>",
            nargs="+",
            help=_("Interconnection(s) to delete (name or ID)"),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        # this is workaround that we have to do to avoid patching of original
        # neutronclient
        setattr(client, 'list_interconnections', self._list)
        fails = 0
        for id_or_name in parsed_args.interconnections:
            try:
                id = client.find_resource(constants.API_RESOURCE_NAME,
                                          id_or_name)['id']
                client.delete(PATH_SINGLE + id)
                LOG.warning("Interconnection %(id)s deleted", {'id': id})
            except Exception as e:
                fails += 1
                LOG.error("Failed to delete Interconnection with name or ID "
                          "'%(id_or_name)s': %(e)s",
                          {'id_or_name': id_or_name, 'e': e})
        if fails > 0:
            msg = (_("Failed to delete %(fails)s of %(total)s "
                     "Interconnection.")
                   % {'fails': fails,
                      'total': len(parsed_args.interconnections)})
            raise exceptions.CommandError(msg)

    def _list(self, retrieve_all=True, **_params):
        client = self.app.client_manager.neutronclient
        return client.list(constants.API_COLLECTION_NAME, PATH_COLLECTION,
                           retrieve_all=retrieve_all, **_params)


class ListInterconnection(command.Lister):
    _description = _("List Interconnection resources")

    def get_parser(self, prog_name):
        parser = super(ListInterconnection, self).get_parser(prog_name)
        nc_osc_utils.add_project_owner_option_to_parser(parser)
        parser.add_argument(
            '--long',
            action='store_true',
            help=_("List additional fields in output"),
        )
        parser.add_argument(
            '--property',
            metavar="<key=value>",
            default=dict(),
            help=_("Filter property to apply on returned Interconnections "
                   "(repeat to filter on multiple properties)"),
            action=KeyValueAction,
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        params = {}
        if parsed_args.project is not None:
            project_id = nc_osc_utils.find_project(
                self.app.client_manager.identity,
                parsed_args.project,
                parsed_args.project_domain,
            ).id
            params['project_id'] = project_id
        if parsed_args.property:
            params.update(parsed_args.property)
        objs = client.list(
            constants.API_COLLECTION_NAME, PATH_COLLECTION, retrieve_all=True,
            **params)[constants.API_COLLECTION_NAME]
        headers, columns = column_util.get_column_definitions(
            _attr_map, long_listing=parsed_args.long)
        return (headers, (osc_utils.get_dict_properties(
            s, columns, formatters=_formatters) for s in objs))


class ShowInterconnection(command.ShowOne):
    _description = _("Show information of a given Interconnection")
    _path = '/interconnection/interconnections/%s'

    def get_parser(self, prog_name):
        parser = super(ShowInterconnection, self).get_parser(prog_name)
        parser.add_argument(
            'interconnection',
            metavar="<interconnection>",
            help=_("Interconnection to display (name or ID)"),
        )
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.neutronclient
        # this is workaround that we have to do to avoid patching of original
        # neutronclient
        setattr(client, 'list_interconnections', self._list)
        id = client.find_resource(
            constants.API_RESOURCE_NAME, parsed_args.interconnection)['id']
        obj = client.get(PATH_SINGLE + id)[constants.API_RESOURCE_NAME]
        columns, display_columns = column_util.get_columns(obj, _attr_map)
        data = osc_utils.get_dict_properties(obj, columns,
                                             formatters=_formatters)
        return display_columns, data

    def _list(self, retrieve_all=True, **_params):
        client = self.app.client_manager.neutronclient
        return client.list(constants.API_COLLECTION_NAME, PATH_COLLECTION,
                           retrieve_all=retrieve_all, **_params)
