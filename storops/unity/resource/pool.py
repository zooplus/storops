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

from storops.unity.resource import UnityResource, \
    UnityAttributeResource, UnityResourceList
import storops.unity.resource.filesystem

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


class UnityPool(UnityResource):
    def create_filesystem(self, nas_server, name, size,
                          proto=None, is_thin=None, tiering_policy=None):
        clz = storops.unity.resource.filesystem.UnityFileSystem
        return clz.create(self._cli, self,
                          nas_server=nas_server,
                          name=name,
                          size=size,
                          proto=proto,
                          is_thin=is_thin,
                          tiering_policy=tiering_policy)


class UnityPoolList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityPool


class UnityPoolTier(UnityAttributeResource):
    pass


class UnityPoolTierList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityPoolTier


class UnityPoolUnit(UnityResource):
    pass


class UnityPoolUnitList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityPoolUnit


class UnityPoolFastVp(UnityAttributeResource):
    pass
