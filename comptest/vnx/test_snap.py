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

from hamcrest import assert_that, equal_to, only_contains, none

__author__ = 'Cedric Zhuang'


def test_snap_create(gf):
    assert_that(gf.snap.existed, equal_to(True))
    assert_that(gf.snap.source_luns, only_contains(gf.lun.lun_id))
    assert_that(gf.snap.primary_luns, only_contains(gf.lun.lun_id))


def test_attach_detach_snap(gf):
    smp_name = gf.add_lun_name()
    smp = gf.lun.create_mount_point(name=smp_name)
    smp.attach_snap(gf.snap)
    smp.update()
    assert_that(smp.attached_snapshot.name, equal_to(gf.snap.name))
    smp.detach_snap()
    smp.update()
    assert_that(smp.attached_snapshot, none())


def test_delete_snap(gf):
    snap_name = gf.add_snap_name()
    gf.lun.create_snap(snap_name)
    snap = gf.vnx.get_snap(name=snap_name)
    snap.delete()
    snap.update()
    assert_that(snap.existed, equal_to(False))
