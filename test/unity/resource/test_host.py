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

from unittest import TestCase

from hamcrest import equal_to, assert_that, instance_of

from storops.unity.enums import HostTypeEnum, HostManageEnum
from storops.unity.resource.health import UnityHealth
from storops.unity.resource.host import UnityHost, UnityHostContainer, \
    UnityHostInitiatorList, UnityHostIpPortList, UnityHostList
from storops.unity.resource.vmware import UnityDataStoreList, UnityVmList
from test.unity.rest_mock import t_rest, patch_rest

__author__ = 'Cedric Zhuang'


class UnityHotTest(TestCase):
    @patch_rest()
    def test_properties(self):
        host = UnityHost(_id='Host_1', cli=t_rest())
        assert_that(host.id, equal_to('Host_1'))
        assert_that(host.type, equal_to(HostTypeEnum.HOST_AUTO))
        assert_that(host.auto_manage_type, equal_to(HostManageEnum.VMWARE))
        assert_that(host.health, instance_of(UnityHealth))
        assert_that(host.name, equal_to('10.244.209.90'))
        assert_that(host.description, equal_to(''))
        assert_that(host.os_type, equal_to('VMware ESXi 6.0.0'))
        assert_that(host.host_pushed_uuid,
                    equal_to('5322a3d1-2901-08c3-c39f-f80f41fafe2e'))
        assert_that(host.host_polled_uuid,
                    equal_to('rfc4122.cd9f4de2-78a5-11e3-85bd-f80f41fafe2e'))
        assert_that(str(host.last_poll_time),
                    equal_to('2016-03-03 04:40:13+00:00'))
        assert_that(host.host_container, instance_of(UnityHostContainer))
        assert_that(host.iscsi_host_initiators,
                    instance_of(UnityHostInitiatorList))
        assert_that(host.host_ip_ports, instance_of(UnityHostIpPortList))
        assert_that(host.datastores, instance_of(UnityDataStoreList))
        assert_that(host.vms, instance_of(UnityVmList))

    @patch_rest()
    def test_get_all(self):
        hosts = UnityHostList(cli=t_rest())
        assert_that(len(hosts), equal_to(6))
