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


def test_create_delete_cifs_share_snapshot(unity_gf):
    # create snap
    snap = unity_gf.cifs_share.create_snap(unity_gf.add_snap_name())
    assert_that(unity_gf.cifs_share.storage_resource.id,
                equal_to(snap.storage_resource.id))

    # delete snap
    resp = snap.delete()
    snap.update()
    assert_that(resp.is_ok(), equal_to(True))
    assert_that(snap.existed, equal_to(False))


def test_check_nfs_share_exists(unity_gf):
    assert_that(unity_gf.nfs_share.existed, equal_to(True))


def test_create_delete_nfs_share_snapshot(unity_gf):
    # create snap
    snap = unity_gf.nfs_share.create_snap(unity_gf.add_snap_name())
    assert_that(unity_gf.nfs_share.storage_resource.id,
                equal_to(snap.storage_resource.id))

    # delete snap
    resp = snap.delete()
    snap.update()
    assert_that(resp.is_ok(), equal_to(True))
    assert_that(snap.existed, equal_to(False))


def test_create_snap_based_nfs_share_and_snap(unity_gf):
    snap = unity_gf.nfs_share.create_snap(unity_gf.add_snap_name())

    # create snap based share
    nfs_share = snap.create_nfs_share(name=snap.name)
    assert_that(nfs_share.existed, equal_to(True))

    # create snap of snap based share
    share_snap = nfs_share.create_snap(unity_gf.add_snap_name())
    assert_that(share_snap.existed, equal_to(True))


def test_create_snap_based_cifs_share_and_snap(unity_gf):
    snap = unity_gf.cifs_share.create_snap(unity_gf.add_snap_name())

    # create snap based share
    cifs_share = snap.create_cifs_share(name=snap.name)
    assert_that(cifs_share.existed, equal_to(True))

    # create snap of snap based share
    share_snap = cifs_share.create_snap(unity_gf.add_snap_name())
    assert_that(share_snap.existed, equal_to(True))
