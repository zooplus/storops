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

from hamcrest import equal_to, assert_that, instance_of, raises, only_contains

from storops.exception import UnityHostIpInUseError, UnityResourceNotFoundError
from storops.unity.enums import HostTypeEnum, HostManageEnum, HostPortTypeEnum
from storops.unity.resource.health import UnityHealth
from storops.unity.resource.host import UnityHost, UnityHostContainer, \
    UnityHostInitiatorList, UnityHostIpPortList, UnityHostList, UnityHostIpPort
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

    @patch_rest()
    def test_get_host_with_ip(self):
        host = UnityHost.get_host(t_rest(), '10.244.209.90')
        assert_that(host.ip_list, only_contains('10.244.209.90'))

    @patch_rest()
    def test_get_host_ip_with_mask(self):
        host = UnityHost.get_host(t_rest(), '10.244.209.90/32')
        assert_that(host.ip_list, only_contains('10.244.209.90'))

    @patch_rest()
    def test_create_simple_host(self):
        host = UnityHost.create(t_rest(), name='host1',
                                host_type=HostTypeEnum.HOST_MANUAL,
                                os='customized os')
        assert_that(host.get_id(), equal_to('Host_11'))
        assert_that(host.name, equal_to('host1'))
        assert_that(host.os_type, equal_to('customized os'))

    @patch_rest()
    def test_delete_host_success(self):
        host = UnityHost(cli=t_rest(), _id='Host_11')
        resp = host.delete()
        assert_that(resp.is_ok(), equal_to(True))

    @patch_rest()
    def test_add_ip_port(self):
        host = UnityHost(cli=t_rest(), _id='Host_9')
        port = host.add_ip_port('1.1.1.1')
        assert_that(port.existed, equal_to(True))
        assert_that(port.address, equal_to('1.1.1.1'))

    @patch_rest()
    def test_delete_ip_port(self):
        host = UnityHost(cli=t_rest(), _id='Host_9')
        resp = host.delete_ip_port('1.1.1.1')
        assert_that(resp.is_ok(), equal_to(True))

    @patch_rest()
    def test_delete_host_and_ip_port(self):
        host = UnityHost(cli=t_rest(), _id='Host_1')
        ip_port = host.host_ip_ports[0]
        resp = host.delete()
        assert_that(resp.is_ok(), equal_to(True))
        assert_that(ip_port.delete, raises(UnityResourceNotFoundError))


class UnityHostIpPortTest(TestCase):
    @patch_rest()
    def test_properties(self):
        ip_port = UnityHostIpPort(cli=t_rest(), _id='HostNetworkAddress_1')
        assert_that(ip_port.host, instance_of(UnityHost))
        assert_that(ip_port.address, equal_to('10.244.209.90'))
        assert_that(ip_port.type, equal_to(HostPortTypeEnum.IPv4))

    @patch_rest()
    def test_get_all(self):
        ip_ports = UnityHostIpPortList(cli=t_rest())
        assert_that(len(ip_ports), equal_to(8))

    @patch_rest()
    def test_create_success(self):
        ip_port = UnityHostIpPort.create(t_rest(), 'Host_9', '1.1.1.1')
        assert_that(ip_port.address, equal_to('1.1.1.1'))
        assert_that(ip_port.type, equal_to(HostPortTypeEnum.IPv4))
        assert_that(ip_port.existed, equal_to(True))

    @patch_rest()
    def test_create_ip_in_use(self):
        def f():
            UnityHostIpPort.create(t_rest(), 'Host_1', '1.1.1.1')

        assert_that(f, raises(UnityHostIpInUseError, 'already exists'))

    @patch_rest()
    def test_delete_success(self):
        ip_port = UnityHostIpPort(cli=t_rest(), _id='HostNetworkAddress_10')
        resp = ip_port.delete()
        assert_that(resp.is_ok(), equal_to(True))

    @patch_rest()
    def test_get_by_ip(self):
        ip_ports = UnityHostIpPortList(cli=t_rest(), address='10.244.209.90')
        assert_that(len(ip_ports), equal_to(1))
        assert_that(ip_ports[0].address, equal_to('10.244.209.90'))
