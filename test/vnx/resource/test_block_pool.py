# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, raises, equal_to, is_in

from test.vnx.cli_mock import t_cli, patch_cli
from test.vnx.resource.verifiers import verify_pool_0
from vnxCliApi.exception import VNXRemovePoolError, VNXCreatePoolError
from vnxCliApi.vnx.resource.block_pool import VNXPool, VNXPoolList, \
    VNXPoolFeature

__author__ = 'Cedric Zhuang'


class VNXPoolTest(TestCase):
    @staticmethod
    def get_pool_with_id(pool_id=0):
        return VNXPool(pool_id=pool_id, cli=t_cli())

    @staticmethod
    def get_pool_with_name(name='Pool4File'):
        return VNXPool(name=name, cli=t_cli())

    @patch_cli()
    def test_property_not_exist(self):
        def f():
            pool = VNXPool(pool_id=0)
            getattr(pool, '_abc')

        assert_that(f, raises(AttributeError))

    @patch_cli()
    def test_pool_by_id(self):
        pool = self.get_pool_with_id()
        verify_pool_0(pool)

    @patch_cli()
    def test_get_pool_get_all(self):
        pools = VNXPool.get(t_cli())
        assert_that(len(pools), equal_to(5))

    @patch_cli()
    def test_get_pool_from_list(self):
        pools = VNXPool.get(t_cli())
        pool = pools[0]
        # no error should be thrown here
        pool.update()

    @patch_cli()
    def test_get_pool_get_by_name(self):
        pool = VNXPool.get(t_cli(), name='Pool4File')
        verify_pool_0(pool)

    @patch_cli()
    def test_get_pool_get_by_id(self):
        pool = VNXPool.get(t_cli(), pool_id=0)
        verify_pool_0(pool)

    @patch_cli()
    def test_pool_by_name(self):
        pool = self.get_pool_with_name()
        verify_pool_0(pool)

    @patch_cli()
    def test_get_lun(self):
        pool = VNXPool(pool_id=1, cli=t_cli())
        lun_list = pool.get_lun()
        assert_that(len(lun_list), equal_to(50))
        for lun in lun_list:
            assert_that(lun.pool_name, equal_to(pool.name))

    @patch_cli()
    def test_get_disk(self):
        pool = VNXPool(pool_id=1, cli=t_cli())
        assert_that(len(pool.disks), equal_to(2))
        disk = pool.disks[0]
        assert_that(disk.serial_number, is_in(('W7H59L3G', 'Z1Y3F94M')))

    @patch_cli()
    def test_create_pool(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'])

        assert_that(f, raises(VNXCreatePoolError,
                              'less than minimum required'))

    @patch_cli()
    def test_create_pool_invalid_disk_number(self):
        def f():
            VNXPool.create(t_cli(), 'p0', ['1_0_0', '1_0_1'], 'r_5')

        assert_that(f, raises(VNXCreatePoolError, 'multiple of 5'))

    @patch_cli()
    def test_remove_pool(self):
        def f():
            VNXPool(0, cli=t_cli()).remove()

        assert_that(f, raises(VNXRemovePoolError, 'may not exist'))

    @patch_cli()
    def test_update_with_one_key_only(self):
        pool = VNXPool(0, 'p0', t_cli())
        assert_that(pool.consumed_capacity_gbs, equal_to(540.303))


class VNXPoolListTest(TestCase):
    @staticmethod
    def get_pool_list():
        return VNXPoolList(t_cli())

    @patch_cli()
    def test_pool_list(self):
        pools = self.get_pool_list()
        assert_that(len(pools), equal_to(5))

    @patch_cli()
    def test_update(self):
        pools = self.get_pool_list()
        pools.update()
        # call twice
        pools.update()
        assert_that(len(pools), equal_to(5))


class VNXPoolFeatureTest(TestCase):
    @patch_cli()
    def test_properties(self):
        f = VNXPoolFeature(t_cli())
        assert_that(f.max_pool_luns, equal_to(2100))
        assert_that(f.total_pool_luns, equal_to(1))
