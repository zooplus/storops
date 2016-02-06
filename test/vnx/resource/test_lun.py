# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to, contains_string, has_item, \
    only_contains, raises

from test.vnx.cli_mock import t_cli, patch_cli
from test.vnx.resource.verifiers import verify_lun_0
from vnxCliApi.exception import VNXModifyLunError, VNXCompressionError, \
    VNXDedupError, VNXRemoveLunError, VNXCreateSnapError
from vnxCliApi.vnx.enums import VNXProvisionEnum, VNXTieringEnum, \
    VNXCompressionRate
from vnxCliApi.vnx.resource.lun import VNXLun, VNXLunList
from vnxCliApi.vnx.resource.snap import VNXSnap

__author__ = 'Cedric Zhuang'


class VNXLunTest(TestCase):
    def get_lun(self):
        return VNXLun(lun_id=2, cli=t_cli())

    @patch_cli()
    def test_lun_status(self):
        lun = self.get_lun()
        assert_that(lun.status, equal_to('OK(0x0)'))

    @patch_cli()
    def test_lun_id_setter_str_input(self):
        lun = self.get_lun()
        assert_that(lun.lun_id, equal_to(2))

    def test_lun_provision_default(self):
        lun = VNXLun()
        self.assertEqual(VNXProvisionEnum.THICK, lun.provision)

    def test_lun_provision_thin(self):
        lun = VNXLun()
        lun.is_thin_lun = True
        lun.is_compressed = False
        lun.dedup_state = False
        assert_that(lun.provision, equal_to(VNXProvisionEnum.THIN))

    def test_lun_provision_compressed(self):
        lun = VNXLun()
        lun.is_thin_lun = True
        lun.is_compressed = True
        lun.dedup_state = False
        assert_that(lun.provision, equal_to(VNXProvisionEnum.COMPRESSED))

    def test_lun_provision_dedup(self):
        lun = VNXLun()
        lun.is_thin_lun = True
        lun.is_compressed = False
        lun.dedup_state = True
        assert_that(lun.provision, equal_to(VNXProvisionEnum.DEDUPED))

    def test_lun_provision_str_not_valid(self):
        lun = VNXLun()
        self.assertRaises(AttributeError, setattr, lun, 'provision', 'invalid')

    def test_lun_tier_default(self):
        lun = VNXLun()
        self.assertEqual(VNXTieringEnum.HIGH_AUTO, lun.tier)

    def test_lun_tier_invalid_str(self):
        lun = VNXLun()
        self.assertRaises(AttributeError, setattr, lun, 'tier', 'invalid')

    def test_lun_tier_highest_available(self):
        lun = VNXLun()
        lun.tiering_policy = 'Auto Tier'
        lun.initial_tier = 'Highest Available'
        assert_that(lun.tier, equal_to(VNXTieringEnum.HIGH_AUTO))

    def test_lun_tier_auto(self):
        lun = VNXLun()
        lun.tiering_policy = 'Auto Tier'
        lun.initial_tier = 'Optimize Pool'
        assert_that(lun.tier, equal_to(VNXTieringEnum.AUTO))

    def test_lun_tier_high(self):
        lun = VNXLun()
        lun.tiering_policy = 'Highest Available'
        lun.initial_tier = 'Highest Available'
        assert_that(lun.tier, equal_to(VNXTieringEnum.HIGH))

    def test_lun_tier_low(self):
        lun = VNXLun()
        lun.tiering_policy = 'Lowest Available'
        lun.initial_tier = 'Lowest Available'
        assert_that(lun.tier, equal_to(VNXTieringEnum.LOW))

    def test_lun_tier_no_move_high_tier(self):
        lun = VNXLun()
        lun.tiering_policy = 'No Movement'
        lun.initial_tier = 'Highest Available'
        assert_that(lun.tier, equal_to(VNXTieringEnum.NO_MOVE))

    def test_lun_tier_no_move_optimize_pool(self):
        lun = VNXLun()
        lun.tiering_policy = 'No Movement'
        lun.initial_tier = 'Optimize Pool'
        assert_that(lun.tier, equal_to(VNXTieringEnum.NO_MOVE))

    @patch_cli()
    def test_update(self):
        lun = self.get_lun()
        self.assertEqual(2.0, lun.total_capacity_gb)
        self.assertEqual(VNXProvisionEnum.THIN, lun.provision)
        self.assertEqual(VNXTieringEnum.HIGH_AUTO, lun.tier)

    @patch_cli()
    def test_repr(self):
        lun = self.get_lun()
        assert_that(repr(lun), contains_string('"VNXLun": {'))

    @patch_cli()
    def test_get_snap(self):
        lun = VNXLun(lun_id=196, cli=t_cli())
        assert_that(lun.name, equal_to('Exch-BronzePlan-AppSync-2.2'))
        assert_that(lun.lun_id, equal_to(196))
        snaps = lun.get_snap()
        assert_that(len(snaps), equal_to(13))
        for snap in snaps:
            assert_that(snap.source_luns, has_item(lun.lun_id))

    @patch_cli()
    def test_get_lun_by_id(self):
        lun = VNXLun(lun_id=0, cli=t_cli())
        lun.update()
        verify_lun_0(lun)

    @patch_cli()
    def test_get_lun_by_name(self):
        lun = VNXLun(name='x', cli=t_cli())
        lun.update()
        verify_lun_0(lun)

    @patch_cli()
    def test_get_lun_list(self):
        assert_that(len(VNXLun.get(t_cli())), equal_to(180))

    @patch_cli()
    def test_create(self):
        lun = VNXLun.create(t_cli(),
                            pool_id=0,
                            lun_id=2,
                            size_gb=2)
        assert_that(lun.user_capacity_gbs, equal_to(2.0))

    def test_get_lun_id_str(self):
        assert_that(VNXLun.get_id('123'), equal_to(123))

    def test_get_lun_obj_member(self):
        lun = VNXLun(lun_id=12)
        assert_that(VNXLun.get_id(lun), equal_to(12))

    @patch_cli()
    def test_get_lun_obj_property(self):
        lun = VNXLun(name='x', cli=t_cli())
        assert_that(VNXLun.get_id(lun), equal_to(0))

    def test_get_lun_id_int(self):
        assert_that(VNXLun.get_id(23), equal_to(23))

    def test_get_lun_id_err(self):
        def f():
            VNXLun.get_id('abc')

        assert_that(f, raises(ValueError, 'invalid lun number'))

    @patch_cli()
    def test_get_migration_session(self):
        lun = VNXLun(lun_id=0, cli=t_cli())
        ms = lun.get_migration_session()
        assert_that(ms.existed, equal_to(True))

    @patch_cli()
    def test_create_mount_point(self):
        lun = VNXLun(name='l1', cli=t_cli())
        m1 = lun.create_mount_point(mount_point_name='m1')
        assert_that(m1.name, equal_to('m1'))
        assert_that(m1.lun_id, equal_to(4057))
        assert_that(m1.attached_snapshot, equal_to('s1'))
        m2 = lun.create_mount_point(mount_point_name='m2')
        assert_that(lun.snapshot_mount_points, only_contains(4056, 4057))
        assert_that(m2.attached_snapshot, equal_to('N/A'))

    @patch_cli()
    def test_attach_snap(self):
        m1 = VNXLun(name='m1', cli=t_cli())
        s1 = VNXSnap(name='s1', cli=t_cli())
        m1.attach_snap(s1)
        m1.update()
        assert_that(m1.attached_snapshot, equal_to('s1'))

    @patch_cli()
    def test_change_name(self):
        l = VNXLun(name='m1', cli=t_cli())
        l.name = 'l1'
        assert_that(l.name, equal_to('l1'))

    @patch_cli()
    def test_change_name_not_found(self):
        def f():
            l = VNXLun(lun_id=4000, cli=t_cli())
            l.name = 'l1'

        assert_that(f, raises(VNXModifyLunError, 'may not exist'))

    @patch_cli()
    def test_change_name_failed(self):
        l = VNXLun(name='l1', cli=t_cli())
        try:
            l.name = 'l3'
            self.fail('should have raised an exception.')
        except VNXModifyLunError:
            assert_that(l._get_name(), equal_to('l1'))

    @patch_cli()
    def test_change_tier(self):
        def f():
            l = VNXLun(lun_id=4000, cli=t_cli())
            l.tier = VNXTieringEnum.LOW

        assert_that(f, raises(VNXModifyLunError, 'may not exist'))

    @patch_cli()
    def test_expand(self):
        def f():
            l = VNXLun(lun_id=0, cli=t_cli())
            l.expand(999999)

        assert_that(f, raises(VNXModifyLunError,
                              'capacity specified is not supported'))

    def test_get_id(self):
        l1 = VNXLun(lun_id=11)
        assert_that(VNXLun.get_id(l1), equal_to(11))

    @patch_cli()
    def test_get_id_with_update(self):
        m1 = VNXLun(name='m1', cli=t_cli())
        assert_that(VNXLun.get_id(m1), equal_to(4057))

    def test_get_id_list(self):
        l22 = VNXLun(lun_id=22)
        l23 = VNXLun(lun_id=23)
        assert_that(VNXLun.get_id_list(l22, l23), only_contains(22, 23))

    @patch_cli()
    def test_enable_compression(self):
        def method():
            l1 = VNXLun(lun_id=19, cli=t_cli())
            l1.enable_compression(VNXCompressionRate.HIGH)

        def prop():
            l1 = VNXLun(lun_id=19, cli=t_cli())
            l1.is_compressed = True

        assert_that(method, raises(VNXCompressionError, 'already turned on'))
        assert_that(prop, raises(VNXCompressionError, 'not installed'))

    @patch_cli()
    def test_disable_compression(self):
        def method():
            l1 = VNXLun(lun_id=19, cli=t_cli())
            l1.disable_compression()

        def prop():
            l1 = VNXLun(lun_id=19, cli=t_cli())
            l1.is_compressed = False

        assert_that(method, raises(VNXCompressionError, 'not turned on'))
        assert_that(prop, raises(VNXCompressionError, 'not turned on'))

    @patch_cli()
    def test_enable_dedup(self):
        def method_call():
            l1 = VNXLun(name='l1', cli=t_cli())
            l1.enable_dedup()

        def set_property():
            l1 = VNXLun(name='l1', cli=t_cli())
            l1.is_dedup = True

        assert_that(method_call, raises(VNXDedupError, 'it is migrating'))
        assert_that(set_property, raises(VNXDedupError, 'it is migrating'))

    @patch_cli()
    def test_disable_dedup(self):
        def method_call():
            l1 = VNXLun(name='l1', cli=t_cli())
            l1.disable_dedup()

        def set_property():
            l1 = VNXLun(name='l1', cli=t_cli())
            l1.is_dedup = False

        assert_that(method_call, raises(VNXDedupError, 'disabled or'))
        assert_that(set_property, raises(VNXDedupError, 'disabled or'))

    @patch_cli()
    def test_remove_lun_error(self):
        def f():
            l1 = VNXLun(name='l1', cli=t_cli())
            l1.remove()

        assert_that(f, raises(VNXRemoveLunError, 'failed to remove'))

    @patch_cli()
    def test_create_snap(self):
        def f():
            l1 = VNXLun(lun_id=11, cli=t_cli())
            l1.create_snap('s1')

        assert_that(f, raises(VNXCreateSnapError,
                              'Cannot create the snapshot'))


class VNXLunListTest(TestCase):
    @patch_cli()
    def test_get_lun_list(self):
        assert_that(len(VNXLunList(t_cli())), equal_to(180))
