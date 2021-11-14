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


def filter_resource(resource, filters=None):
    if not filters:
        filters = {}
    for key, value in filters.items():
        if key in resource.keys():
            if not isinstance(value, list):
                value = [value]
            if isinstance(resource[key], list):
                resource_value = resource[key]
            else:
                resource_value = [resource[key]]
            if not set(value).issubset(set(resource_value)):
                return False
    return True


def filter_fields(resource, fields):
    if fields:
        return dict(((key, item) for key, item in resource.items()
                     if key in fields))
    return resource


def is_extension_supported(plugin, ext_alias):
    return ext_alias in plugin.supported_extension_aliases
