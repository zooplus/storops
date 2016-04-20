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

from storops.unity.resource import UnityResource, UnityResourceList

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


class UnityIpPort(UnityResource):
    pass


class UnityIpPortList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityIpPort


class UnityFcPort(UnityResource):
    pass


class UnityFcPortList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityFcPort


class UnityIoModule(UnityResource):
    pass


class UnityIoModuleList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityIoModule


class UnityIoLimitPolicy(UnityResource):
    pass


class UnityIoLimitPolicyList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityIoLimitPolicy


class UnityIoLimitRule(UnityResource):
    pass


class UnityIoLimitRuleList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityIoLimitRule


class UnityIscsiPortal(UnityResource):
    pass


class UnityIscsiPortalList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityIscsiPortal


class UnityEthernetPort(UnityResource):
    pass


class UnityEthernetPortList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityEthernetPort


class UnityIscsiNode(UnityResource):
    pass


class UnityIscsiNodeList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityIscsiNode
