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

from hamcrest import assert_that, equal_to, contains_string, is_not, raises

from test.vnx.cli_mock import t_cli, patch_cli
from vnxCliApi.exception import VNXObjectNotFound
from vnxCliApi.vnx.enums import VNXSPEnum
from vnxCliApi.vnx.resource.vnx_domain import VNXDomainNodeList, \
    VNXNetworkAdmin

__author__ = 'Cedric Zhuang'


class VNXDomainNodeListTest(TestCase):
    @patch_cli()
    def setUp(self):
        self.dnl = VNXDomainNodeList(t_cli())

    @patch_cli()
    def test_iterable(self):
        assert_that(len(self.dnl), equal_to(2))

    @patch_cli()
    def test_get_node(self):
        node = self.dnl.get_node('APM00153906536')
        assert_that(len(node.members), equal_to(2))

    @patch_cli()
    def test_get_node_not_found(self):
        def f():
            node = self.dnl.get_node('abcde')
            assert_that(len(node.members), equal_to(2))

        assert_that(f, raises(VNXObjectNotFound, 'abcde'))

    @patch_cli()
    def test_get_spa_check_ip(self):
        node = self.dnl.get_node('APM00152904560')
        assert_that(node.spa.ip, equal_to('192.168.1.94'))
        assert_that(node.spb.ip, equal_to('192.168.1.95'))
        assert_that(node.control_station.ip, equal_to('192.168.1.93'))

    @patch_cli()
    def test_get_cs_ip(self):
        assert_that(VNXDomainNodeList.get_cs_ip('APM00153042305', t_cli()),
                    equal_to('192.168.1.93'))


class VNXDomainMemberListTest(TestCase):
    @patch_cli(output='domain_-list_normal.txt')
    def setUp(self):
        dnl = VNXDomainNodeList(t_cli())
        self.dml = dnl[0].members

    @patch_cli()
    def test_iterable(self):
        count = 0
        for _ in self.dml:
            count += 1
        assert_that(count, equal_to(3))

    @patch_cli()
    def test_properties(self):
        str_value = str(self.dml)
        assert_that(str_value, contains_string('VNXDomainMember'))
        assert_that(str_value, contains_string('VNXDomainMemberList'))
        assert_that(str_value, is_not(contains_string('::')))

    @patch_cli()
    def test_sp(self):
        spa = self.dml.spa
        assert_that(spa.ip, equal_to('10.244.211.30'))
        assert_that(spa.is_master, equal_to(True))
        spb = self.dml.spb
        assert_that(spb.ip, equal_to('10.244.211.31'))
        assert_that(spb.is_master, equal_to(False))
        cs = self.dml.control_station
        assert_that(cs.ip, equal_to('10.244.211.32'))


class VNXNetworkAdminTest(TestCase):
    @patch_cli()
    def test_properties(self):
        sp = VNXNetworkAdmin(VNXSPEnum.SP_A, t_cli())
        with sp.with_no_poll():
            assert_that(sp.name, equal_to('vnx2_1_52'))
            assert_that(sp.sp, equal_to(VNXSPEnum.SP_A))
            assert_that(sp.link_status, equal_to('Link-Up'))
            assert_that(sp.subnet_mask, equal_to('255.255.255.0'))
            assert_that(sp.ip, equal_to('192.168.1.52'))
            assert_that(sp.ip_mode, equal_to('Manual'))
            assert_that(sp.gateway, equal_to('192.168.1.1'))
            assert_that(sp.virtual_port_id, equal_to(0))
            assert_that(sp.ipv6_enabled, equal_to(False))
            assert_that(sp.port_id, equal_to(0))
            assert_that(sp.vlan_id, equal_to(None))

    @patch_cli()
    def test_get_spa_ip(self):
        assert_that(VNXNetworkAdmin.get_spa_ip(t_cli()),
                    equal_to('192.168.1.52'))

    @patch_cli()
    def test_get_spb_ip(self):
        assert_that(VNXNetworkAdmin.get_spb_ip(t_cli()),
                    equal_to('192.168.1.53'))
