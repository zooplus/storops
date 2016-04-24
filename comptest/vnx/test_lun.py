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

import pytest
from hamcrest import assert_that, equal_to, raises
from retryz import retry

from comptest import t_vnx
from storops.exception import VNXLunExtendError, VNXDedupAlreadyEnabled, \
    VNXLunPreparingError, VNXNotReadyExpandError
from storops.vnx.enums import VNXProvisionEnum, VNXTieringEnum

__author__ = 'Cedric Zhuang'

vnx = t_vnx()


def test_create_thick_lun(gf):
    assert_that(gf.lun.existed, equal_to(True))
    assert_that(gf.lun.provision, equal_to(VNXProvisionEnum.THICK))
    assert_that(gf.lun.tier, equal_to(VNXTieringEnum.HIGH_AUTO))


@pytest.mark.skipif(not vnx.is_auto_tiering_enabled(),
                    reason='auto tiering not available')
def test_create_typed_lun(gf):
    lun_name = gf.add_lun_name()
    lun = gf.pool.create_lun(lun_name, provision=VNXProvisionEnum.THIN,
                             tier=VNXTieringEnum.NO_MOVE)
    assert_that(lun.existed, equal_to(True))
    assert_that(lun.provision, equal_to(VNXProvisionEnum.THIN))
    assert_that(lun.tier, equal_to(VNXTieringEnum.NO_MOVE))


@pytest.mark.skipif(not vnx.is_compression_enabled(),
                    reason='compression not available')
def test_create_compression_lun(gf):
    lun_name = gf.add_lun_name()
    lun = gf.pool.create_lun(
        lun_name, provision=VNXProvisionEnum.COMPRESSED)
    assert_that(lun.existed, equal_to(True))
    assert_that(lun.provision, equal_to(VNXProvisionEnum.COMPRESSED))


@pytest.mark.skipif(not vnx.is_dedup_enabled(),
                    reason='dedup feature not available')
def test_dedup_lun(gf):
    lun_name = gf.add_lun_name()
    lun = gf.pool.create_lun(
        lun_name, provision=VNXProvisionEnum.DEDUPED)
    assert_that(lun.existed, equal_to(True))

    def f():
        lun.enable_dedup()

    assert_that(f, raises(VNXDedupAlreadyEnabled))


@pytest.mark.skipif(not vnx.is_snap_enabled(),
                    reason='snap feature not available')
def test_create_smp(gf):
    smp_name = gf.add_lun_name()
    smp = gf.lun.create_mount_point(name=smp_name)
    assert_that(smp.existed, equal_to(True))
    assert_that(smp.primary_lun.name, equal_to(gf.lun.name))


def _extend_retry_err(ex):
    return isinstance(ex, (VNXLunPreparingError, VNXNotReadyExpandError))


def test_extend_lun(gf):
    @retry(on_error=_extend_retry_err, wait=7)
    def do_expand():
        lun.expand(2)

    lun = gf.pool.create_lun(gf.add_lun_name())
    assert_that(lun.user_capacity_gbs, equal_to(1.0))
    do_expand()

    def f():
        lun.expand(1)

    assert_that(f, raises(VNXLunExtendError))
