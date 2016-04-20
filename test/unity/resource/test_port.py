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

from hamcrest import assert_that, equal_to, instance_of

from storops.unity.resource.port import UnityIpPort, UnityIpPortList
from storops.unity.resource.sp import UnityStorageProcessor
from test.unity.rest_mock import t_rest, patch_rest

__author__ = 'Cedric Zhuang'


class UnityIpPortTest(TestCase):
    @patch_rest()
    def test_get_properties(self):
        port = UnityIpPort('spa_eth2', cli=t_rest())
        assert_that(port.name, equal_to('SP A Ethernet Port 2'))
        assert_that(port.short_name, equal_to('Ethernet Port 2'))
        assert_that(port.sp, instance_of(UnityStorageProcessor))
        assert_that(port.is_link_up, equal_to(True))
        assert_that(port.mac_address, equal_to('00:60:16:5C:08:E1'))

    @patch_rest()
    def test_get_all(self):
        ports = UnityIpPortList(cli=t_rest())
        assert_that(len(ports), equal_to(8))
