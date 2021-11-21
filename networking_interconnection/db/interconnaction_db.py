# Copyright (c) 2015 Orange.
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
import json
import typing

from oslo_log import log
from oslo_utils import uuidutils
import sqlalchemy as sa
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.orm import exc

from neutron_lib.db import api as db_api
from neutron_lib.db import constants as db_const
from neutron_lib.db import model_base
from neutron_lib.db import model_query
from neutron_lib.db import standard_attr
from neutron_lib.db import utils as db_utils

from networking_interconnection.common import constants
from networking_interconnection.extensions import interconnection as intc_exc

LOG = log.getLogger(__name__)


class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


MutableDict.associate_with(JSONEncodedDict)


class HasProjectNotNullable(model_base.HasProject):

    project_id = sa.Column(sa.String(db_const.PROJECT_ID_FIELD_SIZE),
                           index=True,
                           nullable=False)


class Interconnection(standard_attr.HasStandardAttributes, model_base.BASEV2,
                      model_base.HasId, HasProjectNotNullable):
    """Represents a interconnection Object."""
    type = sa.Column(sa.Enum(*constants.TYPES, name="types"), nullable=False)
    state = sa.Column(
        sa.Enum(*constants.STATES, name="states"), nullable=False)
    name = sa.Column(sa.String(255))
    local_resource_id = sa.Column(sa.String(36), nullable=False)
    remote_resource_id = sa.Column(sa.String(36), nullable=False)
    remote_region = sa.Column(sa.String(255), nullable=False)
    remote_interconnection_id = sa.Column(sa.String(36))
    local_parameters = sa.Column(JSONEncodedDict, nullable=True)
    remote_parameters = sa.Column(JSONEncodedDict, nullable=True)

    # standard attributes support:
    api_collections = [intc_exc.COLLECTION_NAME]
    collection_resource_map = {intc_exc.COLLECTION_NAME:
                               intc_exc.RESOURCE_NAME}


class InterconnectionPluginDb(object):
    """Interconnection service plugin database class using SQLAlchemy models.
    """

    @db_api.CONTEXT_READER
    def _make_dict(self, db_obj: Interconnection,
                   fields: typing.Optional[list]=None):
        res = {
            'id': db_obj['id'],
            'project_id': db_obj['project_id'],
            'name': db_obj['name'],
            'type': db_obj['type'],
            'state': db_obj['state'],
            'local_resource_id': db_obj['local_resource_id'],
            'remote_resource_id': db_obj['remote_resource_id'],
            'remote_region': db_obj['remote_region'],
            'remote_interconnection_id': db_obj['remote_interconnection_id'],
            'local_parameters': db_obj['local_parameters'],
            'remote_parameters': db_obj['remote_parameters'],
        }

        return db_utils.resource_fields(res, fields)

    @db_api.CONTEXT_WRITER
    def create_interconnection(self, context, data: dict) -> dict:
        with db_api.CONTEXT_WRITER.using(context):
            interconnection_db = Interconnection(
                id=uuidutils.generate_uuid(),
                project_id=data['project_id'],
                name=data['name'],
                type=data['type'],
                state=data['state'],
                local_resource_id=data['local_resource_id'],
                remote_resource_id=data['remote_resource_id'],
                remote_region=data['remote_region'],
                remote_interconnection_id=data['remote_interconnection_id'],
                local_parameters=data['local_parameters'],
                remote_parameters=data['remote_parameters'],
            )
            context.session.add(interconnection_db)

        return self._make_dict(interconnection_db)

    @db_api.CONTEXT_READER
    def get_interconnections(self, context,
                             filters: typing.Optional[dict]=None,
                             fields: typing.Optional[list]=None):
        db_objs = model_query.get_collection(
            context, Interconnection, None,
            filters=filters, fields=fields)
        return [self._make_dict(obj, fields=fields) for obj in db_objs]

    @db_api.CONTEXT_READER
    def _get_interconnection(self, context, id: str):
        try:
            return model_query.get_by_id(context, Interconnection, id)
        except exc.NoResultFound:
            raise intc_exc.NotFound(id=id)

    @db_api.CONTEXT_READER
    def get_interconnection(self, context, id: str,
                            fields: typing.Optional[list]=None):
        db_obj = self._get_interconnection(context, id)
        return self._make_dict(db_obj, fields)

    @db_api.CONTEXT_WRITER
    def update_interconnection(self, context, id: str, data: dict):
        db_obj = self._get_interconnection(context, id)
        if data:
            db_obj.update(data)
        return self._make_dict(db_obj)

    @db_api.CONTEXT_WRITER
    def delete_interconnection(self, context, id: str):
        db_obj = self._get_interconnection(context, id)
        interconnection = self._make_dict(db_obj)
        context.session.delete(db_obj)
        return interconnection
