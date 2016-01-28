# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to

from test.vnx.cli_mock import patch_cli, t_vnx
from test.vnx.resource.verifiers import verify_pool_0
from vnxCliApi.vnx.enums import VNXLunType
from vnxCliApi.vnx.resource.lun import VNXLun

__author__ = 'Cedric Zhuang'


class VNXSystemTest(TestCase):
    @patch_cli()
    def setUp(self):
        self.vnx = t_vnx()

    @patch_cli()
    def test_properties(self):
        assert_that(self.vnx.model, equal_to("VNX5800"))
        assert_that(self.vnx.model_type, equal_to('Rackmount'))
        assert_that(self.vnx.serial, equal_to('APM00153042305'))
        assert_that(self.vnx.agent_rev, equal_to('7.33.8 (2.97)'))
        assert_that(self.vnx.name, equal_to('K10'))
        assert_that(self.vnx.revision, equal_to('05.33.008.3.297'))
        assert_that(self.vnx.existed, equal_to(True))

    @patch_cli()
    def test_get_pool_list(self):
        pool_list = self.vnx.get_pool()
        assert_that(len(pool_list), equal_to(5))

    @patch_cli()
    def test_get_pool(self):
        pool = self.vnx.get_pool(pool_id=0)
        verify_pool_0(pool)

    @patch_cli()
    def test_member_ip(self):
        vnx = self.vnx
        assert_that(vnx.spa_ip, equal_to('192.168.1.52'))
        assert_that(vnx.spb_ip, equal_to('192.168.1.53'))
        assert_that(vnx.control_station_ip, equal_to('192.168.1.93'))

    @patch_cli()
    def test_get_snap(self):
        snaps = self.vnx.get_snap()
        assert_that(len(snaps), equal_to(47))

        snap = self.vnx.get_snap('gan_snap')
        assert_that(snap.creation_time, equal_to('05/24/13 20:06:12'))

    @patch_cli()
    def test_get_port(self):
        ports = self.vnx.get_port()
        assert_that(len(ports), equal_to(20))

    @patch_cli()
    def test_get_migration_session_list(self):
        ms_list = self.vnx.get_migration_session()
        assert_that(len(ms_list), equal_to(2))

    @patch_cli()
    def test_get_migration_session(self):
        source = VNXLun(lun_id=0)
        ms = self.vnx.get_migration_session(source)
        assert_that(ms.existed, equal_to(True))

    @patch_cli()
    def test_get_snap_lun(self):
        snap_luns = self.vnx.get_lun(lun_type=VNXLunType.SNAP_MOUNT_POINT)
        assert_that(len(snap_luns), equal_to(45))
        for snap_lun in snap_luns:
            assert_that(snap_lun.is_snap_mount_point, equal_to(True))

    @patch_cli()
    def test_pool_feature(self):
        pf = self.vnx.get_pool_feature()
        assert_that(pf.max_pool_luns, equal_to(2100))
        assert_that(pf.total_pool_luns, equal_to(3))
