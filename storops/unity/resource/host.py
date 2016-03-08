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

from storops.unity.resource import UnityResource, UnityResourceList, \
    UnityAttributeResource

__author__ = 'Cedric Zhuang'


class UnityBlockHostAccess(UnityAttributeResource):
    pass


class UnityBlockHostAccessList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityBlockHostAccess


class UnityHost(UnityResource):
    pass


class UnityHostList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityHost


class UnityHostContainer(UnityResource):
    pass


class UnityHostContainerList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityHostContainer


class UnityHostInitiator(UnityResource):
    pass


class UnityHostInitiatorList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityHostInitiator


class UnityHostInitiatorPath(UnityResource):
    pass


class UnityHostInitiatorPathList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityHostInitiatorPath


class UnityHostIpPort(UnityResource):
    pass


class UnityHostIpPortList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityHostIpPort


class UnityHostLun(UnityResource):
    pass


class UnityHostLunList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityHostLun
