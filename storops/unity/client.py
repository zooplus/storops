# coding=utf-8
# Copyright (c) 2015 EMC Corporation.
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
from __future__ import unicode_literals

import logging

import six

from storops.connection.connector import UnityRESTConnector
import storops.unity.resource.type_resource
from storops.lib.common import instance_cache
from storops.unity.enums import UnityEnum
from storops.unity.resource import UnityResource, UnityResourceList
from storops.unity.resp import RestResponse

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class UnityClient(object):
    def __init__(self, ip, username, password, port=443):
        self._rest = UnityRESTConnector(ip, port=port, user=username,
                                        password=password)

    def get_all(self, type_name, fields=None, _filter=None):
        """Get the resource by resource id.

        :param _filter: dictionary of filter like `{'name': 'abc'}`
        :param type_name: Resource type. For example, pool, lun, nasServer.
        :param fields: Resource fields to return
        :return: List of resource class objects
        """
        fields = self.get_fields(type_name, fields)
        _filter = self.dict_to_filter_string(_filter)

        url = '/api/types/{}/instances'.format(type_name)

        return self.rest_get(url, fields=fields, filter=_filter)

    @classmethod
    def dict_to_filter_string(cls, _filter):
        if _filter:
            items = []
            for k, v in _filter.items():
                if v is None:
                    continue
                if isinstance(v, six.string_types):
                    items.append('{} eq "{}"'.format(k, v))
                else:
                    items.append('{} eq {}'.format(k, v))
            if items:
                ret = ' and '.join(items)
            else:
                ret = None
        else:
            ret = None
        return ret

    def rest_get(self, url, fields=None, **params):
        if fields is None:
            fields = []
        params['fields'] = ','.join(map(str, sorted(fields)))
        url = self.assemble_url(url, **params)
        return RestResponse(self._rest.get(url))

    def rest_post(self, url, body=None, **params):
        url = self.assemble_url(url, **params)
        return RestResponse(self._rest.post(url, body=body))

    def rest_delete(self, url, body=None, **params):
        url = self.assemble_url(url, **params)
        return RestResponse(self._rest.delete(url, body=body))

    @classmethod
    def assemble_url(cls, url, **params):
        if not url.startswith('/'):
            url = '/{}'.format(url)
        if 'compact' not in params:
            params['compact'] = True
        param_list = []
        for key in sorted(params.keys()):
            if params[key] is None:
                continue
            param_list.append('{}={}'.format(key, params[key]))
        url = '{}?{}'.format(url, '&'.join(param_list))
        return url

    @instance_cache
    def get_fields(self, type_name, fields=None):
        if fields is not None:
            ret = fields
        else:
            type_clz = storops.unity.resource.type_resource.UnityType
            unity_type = type_clz(type_name, self)
            ret = unity_type.fields
        return ret

    def get(self, type_name, obj_id, fields=None):
        """Get the resource by resource id.

        :param type_name: Resource type. For example, pool, lun, nasServer.
        :param obj_id: Resource id
        :param fields: Resource fields to return
        :return: List of tuple [(name, res_inst)]
        """
        fields = self.get_fields(type_name, fields)

        url = '/api/instances/{}/{}'.format(
            type_name, obj_id, ','.join(fields))

        return self.rest_get(url, fields=fields)

    def post(self, type_name, **kwargs):
        url = '/api/types/{}/instances'.format(type_name)
        body = self.make_body(kwargs)
        return self.rest_post(url, body)

    def action(self, type_name, obj_id, action, **kwargs):
        base_url = '/api/instances/{}/{}/action/{}'
        url = base_url.format(type_name, obj_id, action)
        body = self.make_body(kwargs)
        return self.rest_post(url, body)

    def type_action(self, type_name, action, **kwargs):
        url = '/api/types/{}/action/{}'.format(type_name, action)
        body = self.make_body(kwargs)
        return self.rest_post(url, body)

    def delete(self, type_name, _id, **kwargs):
        url = '/api/instances/{}/{}'.format(type_name, _id)
        url_params = {'compact': True}
        if 'async' in kwargs:
            async = kwargs['async']
            del kwargs['async']
            if async:
                url_params['timeout'] = 0
        body = self.make_body(kwargs)
        return self.rest_delete(url, body, **url_params)

    @classmethod
    def _is_empty(cls, value):
        if isinstance(value, (dict, tuple, list)) and len(value) == 0:
            ret = True
        else:
            ret = False
        return ret

    @classmethod
    def make_body(cls, value=None, **kwargs):
        if value is None and kwargs:
            value = kwargs
        if isinstance(value, dict):
            ret = {}
            for k, v in value.items():
                v = cls.make_body(v)
                if not cls._is_empty(v) and v is not None:
                    ret[k] = v
        elif isinstance(value, (list, tuple, UnityResourceList)):
            ret = [cls.make_body(v) for v in value]
        elif isinstance(value, UnityEnum):
            ret = value.index
        elif isinstance(value, UnityResource):
            ret = {'id': value.get_id()}
        else:
            ret = value
        return ret
