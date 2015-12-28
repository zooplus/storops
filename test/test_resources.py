# coding=utf-8
from __future__ import unicode_literals
from unittest import TestCase

from hamcrest import assert_that, equal_to, contains_string, is_not, \
    has_item, none, raises, only_contains
from test.cli_mock import patch_cli, read_test_file
from vnxCliApi.cli import CliClient
from vnxCliApi.exception import VNXModifyLunError, VNXConsistencyGroupError, \
    VNXSnapError, VNXStorageGroupError, VNXCompressionError, VNXDedupError
from vnxCliApi.resources import \
    VNXHbaPort, VNXLun, VNXConsistencyGroup, VNXSystem, \
    VNXDomainMemberList, VNXPoolList, VNXPool, VNXLunList, \
    VNXConsistencyGroupList, VNXSPPort, VNXStorageGroupList, VNXStorageGroup, \
    VNXPoolFeature, VNXStorageGroupHBA, VNXConnectionPort, VNXSnap, \
    VNXMigrationSession, VNXNdu
from vnxCliApi.enums import \
    VNXPortTypeEnum, VNXProvisionEnum, VNXTieringEnum, VNXSPEnum, \
    VNXMigrationRate, VNXCompressionRate
from vnxCliApi.parsers import get_parser_config
from test.test_parsers import STORAGE_GROUP_HBA


def test_cli():
    return CliClient("10.244.211.30")


class VNXSystemTest(TestCase):
    @patch_cli()
    def setUp(self):
        self.vnx = VNXSystem('10.244.211.30')

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
    def test_member_ip(self):
        assert_that(self.vnx.spa_ip, equal_to('10.244.211.30'))
        assert_that(self.vnx.spb_ip, equal_to('10.244.211.31'))
        assert_that(self.vnx.control_station_ip, equal_to('10.244.211.32'))

    @patch_cli()
    def test_get_pool_list(self):
        pool_list = self.vnx.get_pool()
        assert_that(len(pool_list), equal_to(5))

    @patch_cli()
    def test_get_pool(self):
        pool = self.vnx.get_pool(pool_id=0)
        validate_pool_0(pool)

    @patch_cli(output='domain_-list_1.txt')
    def test_get_sp_ip(self):
        vnx = VNXSystem('10.110.26.102')
        assert_that(vnx.spa_ip, equal_to('10.110.26.102'))
        assert_that(vnx.spb_ip, equal_to('10.110.26.103'))
        assert_that(vnx.control_station_ip, equal_to('10.110.26.105'))

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


class VNXDomainMemberListTest(TestCase):
    def setUp(self):
        self.dml = VNXDomainMemberList(test_cli())

    @patch_cli()
    def test_iterable(self):
        count = 0
        for _ in self.dml:
            count += 1
        assert_that(count, equal_to(3))

    @patch_cli()
    def test_properties(self):
        str_value = str(self.dml)
        assert_that(str_value, contains_string('VNXDomainMember'))
        assert_that(str_value, contains_string('VNXDomainMemberList'))
        assert_that(str_value, is_not(contains_string('::')))

    @patch_cli()
    def test_sp(self):
        spa = self.dml.spa
        assert_that(spa.ip, equal_to('10.244.211.30'))
        assert_that(spa.is_master, equal_to(True))
        spb = self.dml.spb
        assert_that(spb.ip, equal_to('10.244.211.31'))
        assert_that(spb.is_master, equal_to(False))
        cs = self.dml.control_station
        assert_that(cs.ip, equal_to('10.244.211.32'))


def validate_pool_0(pool):
    assert_that(pool.name, equal_to('Pool4File'))
    assert_that(pool.pool_id, equal_to(0))
    assert_that(pool.state, equal_to('Ready'))
    assert_that(pool.status, equal_to('OK(0x0)'))
    assert_that(pool.fast_cache, equal_to(False))
    assert_that(pool.available_capacity_gbs, equal_to(17314.501))
    assert_that(pool.consumed_capacity_gbs, equal_to(540.303))
    assert_that(pool.total_subscribed_capacity_gbs, equal_to(540.053))
    assert_that(pool.user_capacity_gbs, equal_to(17854.805))
    assert_that(pool.current_operation, equal_to('None'))
    assert_that(pool.current_operation_percent_completed, equal_to(0.0))
    assert_that(pool.current_operation_state, equal_to('N/A'))
    assert_that(pool.current_operation_status, equal_to('N/A'))
    assert_that(pool.luns, equal_to([0]))
    assert_that(pool.percent_full_threshold, equal_to(70.0))
    assert_that(pool.existed, equal_to(True))


class VNXPoolTest(TestCase):
    @staticmethod
    def get_pool_with_id(pool_id=0):
        return VNXPool(pool_id=pool_id, cli=test_cli())

    @staticmethod
    def get_pool_with_name(name='Pool4File'):
        return VNXPool(name=name, cli=test_cli())

    @patch_cli()
    def test_property_not_exist(self):
        def f():
            pool = VNXPool(pool_id=0)
            getattr(pool, '_abc')

        assert_that(f, raises(AttributeError))

    @patch_cli()
    def test_pool_by_id(self):
        pool = self.get_pool_with_id()
        validate_pool_0(pool)

    @patch_cli()
    def test_get_pool_get_all(self):
        pools = VNXPool.get(test_cli())
        assert_that(len(pools), equal_to(5))

    @patch_cli()
    def test_get_pool_from_list(self):
        pools = VNXPool.get(test_cli())
        pool = pools[0]
        # no error should be thrown here
        pool.update()

    @patch_cli()
    def test_get_pool_get_by_name(self):
        pool = VNXPool.get(test_cli(), name='Pool4File')
        validate_pool_0(pool)

    @patch_cli()
    def test_get_pool_get_by_id(self):
        pool = VNXPool.get(test_cli(), pool_id=0)
        validate_pool_0(pool)

    @patch_cli()
    def test_pool_by_name(self):
        pool = self.get_pool_with_name()
        validate_pool_0(pool)

    @patch_cli()
    def test_get_lun(self):
        pool = VNXPool(pool_id=1, cli=test_cli())
        lun_list = pool.get_lun()
        assert_that(len(lun_list), equal_to(50))
        for lun in lun_list:
            assert_that(lun.pool_name, equal_to(pool.name))


class VNXPoolListTest(TestCase):
    @staticmethod
    def get_pool_list():
        return VNXPoolList(test_cli())

    @patch_cli()
    def test_pool_list(self):
        pools = self.get_pool_list()
        assert_that(len(pools), equal_to(5))


class VNXSPPortTest(TestCase):
    @patch_cli()
    def test_port_list(self):
        ports = VNXSPPort.get(test_cli())
        assert_that(len(ports), equal_to(32))

    @patch_cli()
    def test_port_get_sp(self):
        ports = VNXSPPort.get(test_cli(), VNXSPEnum.SP_B)
        assert_that(len(ports), equal_to(16))

    @patch_cli()
    def test_port_get_id(self):
        ports = VNXSPPort.get(test_cli(), port_id=5)
        assert_that(len(ports), equal_to(2))

    @patch_cli()
    def test_index_sequence(self):
        # this test will fail if the index is not used as splitter is wrong
        port = VNXSPPort.get(test_cli(), VNXSPEnum.SP_A, 15)
        assert_that(port.wwn, equal_to(
            '50:06:01:60:B6:E0:16:81:50:06:01:67:36:E4:16:81'))

    @patch_cli()
    def test_get_port(self):
        port = VNXSPPort.get(test_cli(), VNXSPEnum.SP_A, 0)
        assert_that(port.sp, equal_to(VNXSPEnum.SP_A))
        assert_that(port.port_id, equal_to(0))
        assert_that(port.wwn, equal_to(
            '50:06:01:60:B6:E0:16:81:50:06:01:60:36:E0:16:81'))
        assert_that(port.link_status, equal_to('Up'))
        assert_that(port.port_status, equal_to('Online'))
        assert_that(port.switch_present, equal_to(True))
        assert_that(port.speed_value, equal_to('8Gbps'))
        assert_that(port.registered_initiators, equal_to(3))
        assert_that(port.logged_in_initiators, equal_to(1))
        assert_that(port.not_logged_in_initiators, equal_to(2))


class VNXHbaPortTest(TestCase):
    def test_from_storage_group_hba(self):
        hba = VNXStorageGroupHBA.parse(STORAGE_GROUP_HBA)
        port = VNXHbaPort.from_storage_group_hba(hba)
        assert_that(port.sp, equal_to(VNXSPEnum.SP_A))
        assert_that(port.port_id, equal_to(3))
        assert_that(port.vport_id, equal_to(1))
        assert_that(port.type, equal_to(VNXPortTypeEnum.ISCSI))
        assert_that(port.host_initiator_list,
                    has_item('iqn.1991-05.com.microsoft:abc.def.dev'))

    def test_hash(self):
        ports = {
            VNXHbaPort.create(VNXSPEnum.SP_A, 1),
            VNXHbaPort.create(VNXSPEnum.SP_B, 1),
            VNXHbaPort.create(VNXSPEnum.SP_A, 1)
        }
        self.assertEqual(2, len(ports))

    def test_set_sp(self):
        port = VNXHbaPort.create('A', 3)
        self.assertEqual(VNXSPEnum.SP_A, port.sp)

    def test_set_sp_error(self):
        port = VNXHbaPort.create('Z', 3)
        self.assertEqual(False, port.is_valid())
        self.assertIsNone(port.sp)

    def test_set_number_error(self):
        port = VNXHbaPort.create('A', 'a1')
        self.assertEqual(False, port.is_valid())
        self.assertIsNone(port.port_id)

    def test_create_tuple_input(self):
        inputs = ('a', 5)
        port = VNXHbaPort.create(*inputs)
        self.assertEqual(VNXSPEnum.SP_A, port.sp)
        self.assertEqual(5, port.port_id)

    def test_get_sp_index(self):
        port = VNXHbaPort.create('spb', '5')
        self.assertEqual('b', port.get_sp_index())
        self.assertEqual(5, port.port_id)

    def test_equal(self):
        spa_1 = VNXHbaPort.create(VNXSPEnum.SP_A, 1)
        spa_1_dup = VNXHbaPort.create(VNXSPEnum.SP_A, 1)
        spa_2 = VNXHbaPort.create(VNXSPEnum.SP_A, 2)
        self.assertEqual(spa_1, spa_1_dup)
        self.assertEqual(False, spa_1 == spa_2)

    def test_as_tuple(self):
        port = VNXHbaPort.create(VNXSPEnum.SP_A, 1)
        self.assertEqual(('SP A', 1), port.as_tuple())

    def test_repr(self):
        port = VNXHbaPort.create(VNXSPEnum.SP_B, 3)
        self.assertEqual(port.__repr__(),
                         '<VNXPort {sp: SP B, port_id: 3, '
                         'vport_id: 0, host_initiator_list: ()}>')


class VNXConsistencyGroupListTest(TestCase):
    @patch_cli()
    def test_parse(self):
        assert_that(len(VNXConsistencyGroupList(test_cli())), equal_to(2))


class VNXConsistencyGroupTest(TestCase):
    @patch_cli()
    def test_list_consistency_group(self):
        assert_that(len(VNXConsistencyGroup.get(test_cli())), equal_to(2))

    @patch_cli()
    def test_properties(self):
        cg = VNXConsistencyGroup(name="test_cg", cli=test_cli())
        assert_that(cg.name, equal_to('test_cg'))
        assert_that(cg.lun_list, equal_to([1, 3]))
        assert_that(cg.state, equal_to('Ready'))
        assert_that(cg.existed, equal_to(True))

    def test_update(self):
        parser = get_parser_config('VNXConsistencyGroup')
        data = {
            parser.NAME.key: 'test cg name',
            parser.LUN_LIST.key: [1, 5, 7],
            parser.STATE.key: 'Offline'
        }

        cg = VNXConsistencyGroup()
        cg.update(data)

        self.assertEqual('test cg name', cg.name)
        self.assertEqual([1, 5, 7], cg.lun_list)
        self.assertEqual('Offline', cg.state)

    def test_parse(self):
        output = """
                Name:  test cg name
                Name:  another cg
                """
        cgs = VNXConsistencyGroup.parse_all(output)
        self.assertEqual(2, len(cgs))
        names = [cg.name for cg in cgs]
        assert_that(names, has_item('test cg name'))
        assert_that(names, has_item('another cg'))

    @patch_cli()
    def test_add_member(self):
        def f():
            cg = VNXConsistencyGroup('test_cg', test_cli())
            m1 = VNXLun(name='m1', cli=test_cli())
            m2 = VNXLun(name='m2', cli=test_cli())
            cg.add_member(m1, m2)

        assert_that(f, raises(VNXConsistencyGroupError, 'Cannot add members'))


class VNXLunTest(TestCase):
    @property
    def output(self):
        return read_test_file('lun_-list_-all_-l_2.txt')

    def get_lun(self):
        return VNXLun.parse(self.output)

    def test_lun_status(self):
        lun = self.get_lun()
        assert_that(lun.status, equal_to('OK(0x0)'))

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

    def test_update(self):
        lun = self.get_lun()
        self.assertEqual(2.0, lun.total_capacity_gb)
        self.assertEqual(VNXProvisionEnum.THIN, lun.provision)
        self.assertEqual(VNXTieringEnum.HIGH_AUTO, lun.tier)

    def test_repr(self):
        lun = self.get_lun()
        assert_that(repr(lun), contains_string('<VNXLun {'))

    @patch_cli()
    def test_get_snap(self):
        lun = VNXLun(lun_id=196, cli=test_cli())
        assert_that(lun.name, equal_to('Exch-BronzePlan-AppSync-2.2'))
        assert_that(lun.lun_id, equal_to(196))
        snaps = lun.get_snap()
        assert_that(len(snaps), equal_to(13))
        for snap in snaps:
            assert_that(snap.source_luns, has_item(lun.lun_id))

    @staticmethod
    def verify_lun_0(lun):
        assert_that(lun.lun_id, equal_to(0))
        assert_that(lun.name, equal_to('File_CS0_21132_0_d7'))
        assert_that(lun.state, equal_to('Ready'))
        assert_that(lun.current_owner, equal_to(VNXSPEnum.SP_A))
        assert_that(lun.default_owner, equal_to(VNXSPEnum.SP_A))
        assert_that(lun.wwn, equal_to(
            '60:06:01:60:12:60:3D:00:95:63:38:87:9D:69:E5:11'))
        assert_that(lun.operation, equal_to('None'))
        assert_that(lun.pool_name, equal_to('Pool4File'))
        assert_that(lun.is_thin_lun, equal_to(False))
        assert_that(lun.is_compressed, equal_to(False))
        assert_that(lun.is_dedup, equal_to(False))
        assert_that(lun.is_private, equal_to(False))
        assert_that(lun.tier, equal_to(VNXTieringEnum.HIGH_AUTO))
        assert_that(lun.provision, equal_to(VNXProvisionEnum.THICK))
        assert_that(lun.user_capacity_gbs, equal_to(500.0))
        assert_that(lun.consumed_capacity_gbs, equal_to(512.249))
        assert_that(lun.existed, equal_to(True))

    @patch_cli()
    def test_get_lun_by_id(self):
        lun = VNXLun(lun_id=0, cli=test_cli())
        lun.update()
        self.verify_lun_0(lun)

    @patch_cli()
    def test_get_lun_by_name(self):
        lun = VNXLun(name='x', cli=test_cli())
        lun.update()
        self.verify_lun_0(lun)

    @patch_cli()
    def test_get_lun_list(self):
        assert_that(len(VNXLun.get(test_cli())), equal_to(180))

    @patch_cli()
    def test_create(self):
        lun = VNXLun.create(test_cli(),
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
        lun = VNXLun(name='x', cli=test_cli())
        assert_that(VNXLun.get_id(lun), equal_to(0))

    def test_get_lun_id_int(self):
        assert_that(VNXLun.get_id(23), equal_to(23))

    def test_get_lun_id_err(self):
        def f():
            VNXLun.get_id('abc')

        assert_that(f, raises(ValueError, 'invalid lun number'))

    @patch_cli()
    def test_get_migration_session(self):
        lun = VNXLun(lun_id=0, cli=test_cli())
        ms = lun.get_migration_session()
        assert_that(ms.existed, equal_to(True))

    @patch_cli()
    def test_create_mount_point(self):
        lun = VNXLun(name='l1', cli=test_cli())
        m1 = lun.create_mount_point(mount_point_name='m1')
        assert_that(m1.name, equal_to('m1'))
        assert_that(m1.lun_id, equal_to(4057))
        assert_that(m1.attached_snapshot, equal_to('s1'))
        m2 = lun.create_mount_point(mount_point_name='m2')
        assert_that(lun.snapshot_mount_points, only_contains(4056, 4057))
        assert_that(m2.attached_snapshot, equal_to('N/A'))

    @patch_cli()
    def test_attach_snap(self):
        m1 = VNXLun(name='m1', cli=test_cli())
        s1 = VNXSnap(name='s1', cli=test_cli())
        m1.attach_snap(s1)
        m1.update()
        assert_that(m1.attached_snapshot, equal_to('s1'))

    @patch_cli()
    def test_change_name(self):
        l = VNXLun(name='m1', cli=test_cli())
        l.name = 'l1'
        assert_that(l.name, equal_to('l1'))

    @patch_cli()
    def test_change_name_not_found(self):
        def f():
            l = VNXLun(lun_id=4000, cli=test_cli())
            l.name = 'l1'

        assert_that(f, raises(VNXModifyLunError, 'may not exist'))

    @patch_cli()
    def test_change_name_failed(self):
        l = VNXLun(name='l1', cli=test_cli())
        try:
            l.name = 'l3'
            self.fail('should have raised an exception.')
        except VNXModifyLunError:
            assert_that(l._get_name(), equal_to('l1'))

    @patch_cli()
    def test_change_tier(self):
        def f():
            l = VNXLun(lun_id=4000, cli=test_cli())
            l.tier = VNXTieringEnum.LOW

        assert_that(f, raises(VNXModifyLunError, 'may not exist'))

    @patch_cli()
    def test_expand(self):
        def f():
            l = VNXLun(lun_id=0, cli=test_cli())
            l.expand(999999)

        assert_that(f, raises(VNXModifyLunError,
                              'capacity specified is not supported'))

    def test_get_id(self):
        l1 = VNXLun(lun_id=11)
        assert_that(VNXLun.get_id(l1), equal_to(11))

    @patch_cli()
    def test_get_id_with_update(self):
        m1 = VNXLun(name='m1', cli=test_cli())
        assert_that(VNXLun.get_id(m1), equal_to(4057))

    def test_get_id_list(self):
        l22 = VNXLun(lun_id=22)
        l23 = VNXLun(lun_id=23)
        assert_that(VNXLun.get_id_list(l22, l23), only_contains(22, 23))

    @patch_cli()
    def test_enable_compression(self):
        def method():
            l1 = VNXLun(lun_id=19, cli=test_cli())
            l1.enable_compression(VNXCompressionRate.HIGH)

        def prop():
            l1 = VNXLun(lun_id=19, cli=test_cli())
            l1.is_compressed = True

        assert_that(method, raises(VNXCompressionError, 'already turned on'))
        assert_that(prop, raises(VNXCompressionError, 'not installed'))

    @patch_cli()
    def test_disable_compression(self):
        def method():
            l1 = VNXLun(lun_id=19, cli=test_cli())
            l1.disable_compression()

        def prop():
            l1 = VNXLun(lun_id=19, cli=test_cli())
            l1.is_compressed = False

        assert_that(method, raises(VNXCompressionError, 'not turned on'))
        assert_that(prop, raises(VNXCompressionError, 'not turned on'))

    @patch_cli()
    def test_enable_dedup(self):
        def method_call():
            l1 = VNXLun(name='l1', cli=test_cli())
            l1.enable_dedup()

        def set_property():
            l1 = VNXLun(name='l1', cli=test_cli())
            l1.is_dedup = True

        assert_that(method_call, raises(VNXDedupError, 'it is migrating'))
        assert_that(set_property, raises(VNXDedupError, 'it is migrating'))

    @patch_cli()
    def test_disable_dedup(self):
        def method_call():
            l1 = VNXLun(name='l1', cli=test_cli())
            l1.disable_dedup()

        def set_property():
            l1 = VNXLun(name='l1', cli=test_cli())
            l1.is_dedup = False

        assert_that(method_call, raises(VNXDedupError, 'disabled or'))
        assert_that(set_property, raises(VNXDedupError, 'disabled or'))


class VNXLunListTest(TestCase):
    @patch_cli()
    def test_get_lun_list(self):
        assert_that(len(VNXLunList(test_cli())), equal_to(180))


class VNXStorageGroupListTest(TestCase):
    @patch_cli()
    def test_get_sg_list(self):
        assert_that(len(VNXStorageGroupList(test_cli())), equal_to(4))


class VNXStorageGroupTest(TestCase):
    def test_sg(self, name='server7'):
        return VNXStorageGroup(name=name, cli=test_cli())

    @patch_cli()
    def test_properties(self):
        sg = self.test_sg()
        assert_that(sg.name, equal_to('server7'))
        assert_that(
            sg.wwn,
            equal_to('F6:F1:04:29:91:97:E5:11:85:E1:AE:04:FD:64:DC:17'))
        assert_that(sg.shareable, equal_to(True))
        assert_that(len(sg.alu_hlu_map), equal_to(2))
        assert_that(sg.alu_hlu_map[10], equal_to(153))
        assert_that(len(sg.hba_sp_pairs), equal_to(15))
        assert_that(sg.uid, equal_to(sg.wwn))
        assert_that(sg.has_alu(10), equal_to(True))
        assert_that(sg.has_alu(11), equal_to(False))
        assert_that(sg.has_hlu(153), equal_to(True))
        assert_that(sg.has_hlu(11), equal_to(False))
        assert_that(sg.existed, equal_to(True))

    @patch_cli()
    def test_initiator_uid_list(self):
        sg = self.test_sg('microsoft')
        assert_that(len(sg.initiator_uid_list), equal_to(2))
        assert_that(sg.initiator_uid_list,
                    has_item('iqn.1991-05.com.microsoft:abc.def.dev'))

    @patch_cli()
    def test_hba_port_map(self):
        sg = self.test_sg()
        assert_that(len(sg.hba_port_map), equal_to(15))
        assert_that(len(sg.port_list), equal_to(8))
        assert_that(len(sg.initiator_uid_list), equal_to(5))

    @patch_cli()
    def test_attach_hlu(self):
        sg = self.test_sg()
        lun = VNXLun(name='x', cli=test_cli())
        assert_that(sg.has_alu(0), equal_to(False))
        sg.attach_hlu(lun)
        assert_that(sg.has_alu(0), equal_to(True))
        assert_that(sg.get_hlu(0), equal_to(1))

    @patch_cli()
    def test_detach_hlu(self):
        sg = self.test_sg()
        sg.detach_hlu(10)
        assert_that(sg.has_hlu(10), equal_to(False))

    @patch_cli()
    def test_connect_host(self):
        def f():
            sg = self.test_sg()
            sg.connect_host('host1')

        assert_that(f, raises(VNXStorageGroupError,
                              'Host specified is not known'))

    @patch_cli()
    def test_disconnect_host(self):
        def f():
            sg = self.test_sg()
            sg.disconnect_host('host1')

        assert_that(f, raises(VNXStorageGroupError,
                              'not currently connected'))


class VNXPoolFeatureTest(TestCase):
    @patch_cli()
    def test_properties(self):
        f = VNXPoolFeature(test_cli())
        assert_that(f.max_pool_luns, equal_to(2100))
        assert_that(f.total_pool_luns, equal_to(1))


class VNXStorageGroupHBATest(TestCase):
    def test_hba(self):
        return VNXStorageGroupHBA().update(STORAGE_GROUP_HBA)

    def test_properties(self):
        hba = self.test_hba()
        assert_that(hba.host_name, equal_to('abc.def.dev'))
        assert_that(hba.initiator_ip, equal_to('10.244.209.72'))
        assert_that(hba.sp_port, equal_to('A-3v1'))

    def test_sp(self):
        assert_that(self.test_hba().sp, equal_to(VNXSPEnum.SP_A))

    def test_uid(self):
        assert_that(self.test_hba().uid,
                    equal_to('iqn.1991-05.com.microsoft:abc.def.dev'))

    def test_port_id(self):
        assert_that(self.test_hba().port_id, equal_to(3))

    def test_vlan(self):
        assert_that(self.test_hba().vlan, equal_to(1))

    def test_port_type(self):
        assert_that(self.test_hba().port_type,
                    equal_to(VNXPortTypeEnum.ISCSI))


class VNXConnectionPortTest(TestCase):
    def test_port(self):
        return VNXConnectionPort(sp='a', port_id=4, cli=test_cli())

    @patch_cli()
    def test_properties(self):
        port = self.test_port()
        assert_that(port.sp, equal_to(VNXSPEnum.SP_A))
        assert_that(port.port_id, equal_to(4))
        assert_that(port.wwn,
                    equal_to('iqn.1992-04.com.emc:cx.apm00153906536.a4'))
        assert_that(port.iscsi_alias, equal_to('6536.a4'))
        assert_that(port.enode_mac_address, equal_to('00-60-16-45-5D-FC'))
        assert_that(port.virtual_port_id, equal_to(0))
        assert_that(port.vlan_id, none())
        assert_that(port.current_mtu, equal_to(1500))
        assert_that(port.auto_negotiate, equal_to(False))
        assert_that(port.port_speed, equal_to('10000 Mb'))
        assert_that(port.host_window, equal_to('256K'))
        assert_that(port.replication_window, equal_to('256K'))
        assert_that(port.ip_address, equal_to('192.168.4.52'))
        assert_that(port.subnet_mask, equal_to('255.255.255.0'))
        assert_that(port.gateway_address, equal_to('0.0.0.0'))
        assert_that(port.existed, equal_to(True))

    @patch_cli()
    def test_get_all(self):
        ports = VNXConnectionPort.get(test_cli())
        assert_that(len(ports), equal_to(20))

    @patch_cli()
    def test_get_by_sp(self):
        ports = VNXConnectionPort.get(test_cli(), VNXSPEnum.SP_A)
        assert_that(len(ports), equal_to(10))

    @patch_cli()
    def test_get_by_port(self):
        ports = VNXConnectionPort.get(test_cli(), port_id=8)
        assert_that(len(ports), equal_to(2))

    @patch_cli()
    def test_get_single(self):
        port = VNXConnectionPort.get(test_cli(), VNXSPEnum.SP_A, 4)
        assert_that(port, equal_to([]))


class VNXSnapTest(TestCase):
    @patch_cli()
    def test_properties(self):
        snap = VNXSnap('gan_snap', test_cli())
        assert_that(snap.name, equal_to('gan_snap'))
        assert_that(snap.description, equal_to('gan snap'))
        assert_that(snap.creation_time, equal_to('05/24/13 20:06:12'))
        assert_that(snap.last_modify_time, equal_to('07/23/14 12:28:42'))
        assert_that(snap.last_modified_by, equal_to('N/A'))
        assert_that(snap.source_luns, equal_to([57]))
        assert_that(snap.source_cg, equal_to('N/A'))
        assert_that(snap.primary_luns, equal_to([57]))
        assert_that(snap.state, equal_to('Ready'))
        assert_that(snap.status, equal_to('OK(0x0)'))
        assert_that(snap.allow_read_write, equal_to(True))
        assert_that(snap.modified, equal_to(True))
        assert_that(snap.attached_luns, equal_to([]))
        assert_that(snap.allow_auto_delete, equal_to(True))
        assert_that(snap.expiration_date, equal_to('Never'))
        assert_that(snap.existed, equal_to(True))

    @patch_cli()
    def test_get_all(self):
        snaps = VNXSnap.get(test_cli())
        assert_that(len(snaps), equal_to(47))

    @patch_cli()
    def test_get_by_name(self):
        snap = VNXSnap.get(test_cli(), name='gan_snap')
        assert_that(snap.creation_time, equal_to('05/24/13 20:06:12'))

    @patch_cli(output='snap_-list_-detail_error.txt')
    def test_get_not_found(self):
        snap = VNXSnap.get(test_cli(), name='xxx')
        assert_that(snap.existed, equal_to(False))

    @patch_cli()
    def test_copy_snap(self):
        def f():
            src = VNXSnap.get(test_cli(), name='123')
            src.copy('456')

        assert_that(f, raises(VNXSnapError, 'Cannot copy'))

    @patch_cli()
    def test_modify_snap(self):
        snap = VNXSnap(cli=test_cli(), name='s1')
        snap.modify(new_name='s2', rw=True)
        assert_that(snap._name, equal_to('s2'))

    @patch_cli()
    def test_modify_snap_failed(self):
        snap = VNXSnap(cli=test_cli(), name='s2')
        try:
            snap.modify(new_name='s1')
            self.fail('should have raise an exception.')
        except VNXSnapError:
            assert_that(snap._name, equal_to('s2'))


class VNXMigrationSessionTest(TestCase):
    @patch_cli()
    def test_properties(self):
        ms = VNXMigrationSession(0, test_cli())
        assert_that(ms.source_lu_id, equal_to(0))
        assert_that(ms.source_lu_name, equal_to('LUN 0'))
        assert_that(ms.dest_lu_id, equal_to(1))
        assert_that(ms.dest_lu_name, equal_to('LUN 1'))
        assert_that(ms.migration_rate, equal_to(VNXMigrationRate.HIGH))
        assert_that(ms.percent_complete, equal_to(50.0))
        assert_that(ms.time_remaining, equal_to('0 second(s)'))
        assert_that(ms.current_state, equal_to('MIGRATING'))
        assert_that(ms.existed, equal_to(True))

    @patch_cli()
    def test_get_all(self):
        ms_list = VNXMigrationSession.get(test_cli())
        assert_that(len(ms_list), equal_to(2))

    @patch_cli(output='migrate_-list_none.txt')
    def test_get_all_none(self):
        ms_list = VNXMigrationSession.get(test_cli())
        assert_that(len(ms_list), equal_to(0))

    @patch_cli()
    def test_get_no_session(self):
        ms = VNXMigrationSession(10, test_cli())
        assert_that(ms.existed, equal_to(False))

    @patch_cli()
    def test_get_lun_not_exists(self):
        ms = VNXMigrationSession(1234, test_cli())
        assert_that(ms.existed, equal_to(False))


class VNXNduTest(TestCase):
    @patch_cli()
    def test_get_all(self):
        ndu_list = VNXNdu.get(test_cli())
        assert_that(len(ndu_list), equal_to(16))

    @patch_cli()
    def test_get(self):
        ndu = VNXNdu.get(test_cli(), '-VNXSnapshots')
        assert_that(ndu.name, equal_to('-VNXSnapshots'))
        assert_that(ndu.revision, equal_to('-'))
        assert_that(ndu.commit_required, equal_to(False))
        assert_that(ndu.revert_possible, equal_to(False))
        assert_that(ndu.active_state, equal_to(True))
        assert_that(ndu.is_installation_completed, equal_to(True))
        assert_that(ndu.is_this_system_software, equal_to(False))
