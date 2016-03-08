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

from hamcrest import equal_to, assert_that, only_contains, instance_of, raises

from storops.exception import UnityException, UnityNfsShareNameExistedError
from storops.unity.enums import NFSTypeEnum, NFSShareRoleEnum, \
    NFSShareDefaultAccessEnum, NFSShareSecurityEnum
from storops.unity.resource.filesystem import UnityFileSystem
from storops.unity.resource.nfs_share import UnityNfsShare, UnityNfsShareList
from test.unity.rest_mock import patch_rest, t_rest

__author__ = 'Cedric Zhuang'


class UnityNfsShareTest(TestCase):
    @patch_rest()
    def test_properties(self):
        nfs = UnityNfsShare('NFSShare_1', cli=t_rest())
        assert_that(nfs.id, equal_to('NFSShare_1'))
        assert_that(nfs.type, equal_to(NFSTypeEnum.NFS_SHARE))
        assert_that(nfs.role, equal_to(NFSShareRoleEnum.PRODUCTION))
        assert_that(nfs.default_access,
                    equal_to(NFSShareDefaultAccessEnum.ROOT))
        assert_that(nfs.min_security, equal_to(NFSShareSecurityEnum.SYS))
        assert_that(nfs.name, equal_to('esa_nfs1'))
        assert_that(nfs.path, equal_to(r'/'))
        assert_that(nfs.export_paths,
                    only_contains(r'10.244.220.120:/esa_nfs1'))
        assert_that(nfs.description, equal_to('bcd'))
        assert_that(str(nfs.creation_time),
                    equal_to('2016-03-02 02:39:22.856000+00:00'))
        assert_that(str(nfs.modification_time),
                    equal_to('2016-03-02 02:39:22.856000+00:00'))
        assert_that(nfs.filesystem.get_id(), equal_to('fs_1'))
        assert_that(nfs.filesystem, instance_of(UnityFileSystem))

    @patch_rest()
    def test_get_all(self):
        nfs_list = UnityNfsShareList(cli=t_rest())
        assert_that(len(nfs_list), equal_to(2))

    @patch_rest()
    def test_create_nfs_share_fs_not_support(self):
        def f():
            UnityNfsShare.create(t_rest(), 'ns1', 'fs_8')

        assert_that(f, raises(UnityException, 'not support NFS'))

    @patch_rest()
    def test_create_nfs_share_success(self):
        share = UnityNfsShare.create(
            t_rest(), 'ns1', 'fs_9',
            share_access=NFSShareDefaultAccessEnum.READ_WRITE)
        assert_that(share.name, equal_to('ns1'))
        assert_that(share.id, equal_to('NFSShare_4'))

    @patch_rest()
    def test_create_nfs_share_name_exists(self):
        def f():
            UnityNfsShare.create(
                t_rest(), 'ns1', 'fs_9',
                share_access=NFSShareDefaultAccessEnum.ROOT)

        assert_that(f, raises(UnityNfsShareNameExistedError, 'already exists'))

    @patch_rest()
    def test_remove_nfs_share_success(self):
        share = UnityNfsShare(_id='NFSShare_4', cli=t_rest())
        resp = share.remove()
        assert_that(resp.is_ok(), equal_to(True))
