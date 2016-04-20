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

from storops.unity.resource import UnityResource

__author__ = 'Cedric Zhuang'


class UnityType(UnityResource):
    resource_class = 'type'

    _fields = ('name', 'description', 'documentation', 'type',
               'attributes.name', 'attributes.initialValue', 'attributes.type',
               'attributes.description', 'attributes.displayValue')

    def _get_raw_resource(self):
        url = '/api/types/{}'.format(self._id)
        return self._cli.rest_get(url, fields=self._fields)

    @property
    def fields(self):
        if self._id == 'type':
            ret = self._fields
        else:
            ret = tuple(sorted(att['name'] for att in self.attributes))
        return ret

    @property
    def fields_str(self):
        return ','.join(self.fields)
