# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to, has_item, raises

from test.vnx.cli_mock import patch_cli, t_cli
from test.vnx.resource.fakes import STORAGE_GROUP_HBA
from vnxCliApi.exception import VNXStorageGroupError
from vnxCliApi.vnx.enums import VNXSPEnum, VNXPortType
from vnxCliApi.vnx.resource.lun import VNXLun
from vnxCliApi.vnx.resource.sg import VNXStorageGroupList, VNXStorageGroup, \
    VNXStorageGroupHBA

__author__ = 'Cedric Zhuang'


class VNXStorageGroupListTest(TestCase):
    @patch_cli()
    def test_get_sg_list(self):
        assert_that(len(VNXStorageGroupList(t_cli())), equal_to(4))


class VNXStorageGroupTest(TestCase):
    def test_sg(self, name='server7'):
        return VNXStorageGroup(name=name, cli=t_cli())

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
    def test_attach_alu(self):
        sg = self.test_sg()
        lun = VNXLun(name='x', cli=t_cli())
        assert_that(sg.has_alu(0), equal_to(False))
        sg.attach_alu(lun)
        assert_that(sg.has_alu(0), equal_to(True))
        assert_that(sg.get_hlu(0), equal_to(1))

    @patch_cli()
    def test_detach_hlu(self):
        sg = self.test_sg()
        sg.detach_alu(10)
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
                    equal_to(VNXPortType.ISCSI))
