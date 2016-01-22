# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, raises, equal_to, has_items

from test.vnx.cli_mock import patch_cli, t_cli
from test.vnx.resource.verifiers import verify_disk_4_0_e8
from vnxCliApi.vnx.resource.disk import VNXDisk

__author__ = 'Cedric Zhuang'


class VNXDiskTest(TestCase):
    def test_invalid_index(self):
        def f():
            VNXDisk('abcde')

        assert_that(f, raises(ValueError, 'invalid disk index'))

    def test_parse_index(self):
        bus, enc, disk = VNXDisk.parse_index('1_10_A4')
        assert_that(bus, equal_to("1"))
        assert_that(enc, equal_to("10"))
        assert_that(disk, equal_to("A4"))

    def test_parse_index_error(self):
        def f():
            VNXDisk.parse_index('abcdefg')

        assert_that(f, raises(ValueError, 'invalid disk index'))

    @patch_cli()
    def test_get_all(self):
        disks = VNXDisk.get(t_cli())
        assert_that(len(disks), equal_to(180))
        for disk in disks:
            if disk.index == '4_0_e8':
                verify_disk_4_0_e8(disk)
                break

    @patch_cli()
    def test_get_disk(self):
        disk = VNXDisk.get(t_cli(), '4_0_e8')
        verify_disk_4_0_e8(disk)

    @patch_cli()
    def test_remove_disk(self):
        disk = VNXDisk('0_0_1', t_cli())
        ret = disk.remove()
        assert_that(ret, has_items(''))

    @patch_cli()
    def test_install_disk(self):
        disk = VNXDisk('0_0_1', t_cli())
        ret = disk.install()
        assert_that(ret, has_items(''))
