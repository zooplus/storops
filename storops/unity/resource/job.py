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


class UnityJob(UnityResource):
    pass


class UnityJobList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityJob


class UnityJobTask(UnityAttributeResource):
    pass


class UnityJobTaskList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityJobTask


class UnityMessage(UnityAttributeResource):
    pass


class UnityMessageList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityMessage


class UnityLocalizedMessage(UnityAttributeResource):
    pass


class UnityLocalizedMessageList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityLocalizedMessage
