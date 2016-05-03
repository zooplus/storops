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

from hamcrest import assert_that, equal_to

__author__ = 'Cedric Zhuang'


def test_check_cifs_share_exists(unity_gf):
    assert_that(unity_gf.cifs_share.existed, equal_to(True))


def test_check_nfs_share_exists(unity_gf):
    assert_that(unity_gf.nfs_share.existed, equal_to(True))
