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

from hamcrest import assert_that, equal_to, has_item, raises, instance_of
from storops.vnx.resource.port import VNXSPPort, VNXConnectionPort

from test.vnx.cli_mock import patch_cli, t_cli
from test.vnx.resource.fakes import STORAGE_GROUP_HBA
from storops.exception import VNXStorageGroupError, \
    VNXStorageGroupNameInUseError, VNXDetachAluNotFoundError, \
    VNXAluAlreadyAttachedError, VNXAluNotFoundError, VNXAluNumberInUseError, \
    VNXInvalidCliParamError, VNXPortNotInitializedError, \
    VNXInitiatorExistedError
from storops.vnx.enums import VNXSPEnum, VNXPortType
from storops.vnx.resource.lun import VNXLun
from storops.vnx.resource.sg import VNXStorageGroupList, VNXStorageGroup, \
    VNXStorageGroupHBA, VNXStorageGroupHBAList

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
    def test_get_sg_os01(self):
        sg = VNXStorageGroup(name='os01', cli=t_cli())
        assert_that(len(sg.hba_sp_pairs), equal_to(1))
        assert_that(sg.hba_sp_pairs, instance_of(VNXStorageGroupHBAList))
        hba = sg.hba_sp_pairs[0]
        assert_that(hba.sp, equal_to(VNXSPEnum.SP_A))
        assert_that(hba.uid,
                    equal_to('iqn.1993-08.org.debian:01:95bbe389e025'))
        assert_that(hba.port_id, equal_to(4))

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
    def test_attach_alu_success(self):
        sg = self.test_sg()
        lun = VNXLun(name='x', cli=t_cli())
        assert_that(sg.has_alu(0), equal_to(False))
        hlu = sg.attach_alu(lun)
        assert_that(sg.has_alu(0), equal_to(True))
        assert_that(sg.get_hlu(0), equal_to(1))
        assert_that(hlu, equal_to(1))

    @patch_cli()
    def test_attach_alu_already_attached(self):
        def f():
            sg = self.test_sg()
            sg.attach_alu(123)

        assert_that(f, raises(VNXAluAlreadyAttachedError,
                              'already been added'))

    @patch_cli()
    def test_attach_alu_not_found(self):
        def f():
            sg = self.test_sg()
            sg.attach_alu(124)

        assert_that(f, raises(VNXAluNotFoundError,
                              'not a bound ALU number'))

    @patch_cli()
    def test_attach_alu_hlu_in_use_retry(self):
        def f():
            sg = self.test_sg()
            sg.attach_alu(13, retry_limit=2)

        assert_that(f, raises(VNXAluNumberInUseError,
                              'LUN Number already in use'))

    @patch_cli()
    def test_detach_hlu_success(self):
        sg = self.test_sg()
        sg.detach_alu(10)
        assert_that(sg.has_hlu(10), equal_to(False))

    @patch_cli()
    def test_detach_hlu_not_found(self):
        def f():
            sg = self.test_sg()
            sg.detach_alu(1032)

        assert_that(f, raises(VNXDetachAluNotFoundError, 'No such Host LUN'))

    @patch_cli()
    def test_detach_hlu_not_attached(self):
        def f():
            sg = self.test_sg()
            sg.detach_alu(1033)

        assert_that(f, raises(VNXDetachAluNotFoundError,
                              'is not attached'))

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

    @patch_cli()
    def test_create_sg_name_in_use(self):
        def f():
            VNXStorageGroup.create('existed', t_cli())

        assert_that(f, raises(VNXStorageGroupNameInUseError, 'already in use'))


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

    @patch_cli()
    def test_set_path_with_sp_port_invalid_wwn(self):
        def f():
            port = VNXSPPort.get(sp=VNXSPEnum.SP_A, port_id=0, cli=t_cli())
            sg = VNXStorageGroup(cli=t_cli(), name='sg0')
            sg.set_path(port, '11:22:33', 'host0')

        assert_that(f, raises(VNXInvalidCliParamError))

    @patch_cli()
    def test_set_path_with_fc_port_success(self):
        wwn = '01:02:03:04:05:06:07:08:09:0A:0B:0C:0D:0E:0F:10'
        port = VNXSPPort.get(sp=VNXSPEnum.SP_A, port_id=0, cli=t_cli())
        sg = VNXStorageGroup(cli=t_cli(), name='sg0')
        # no exception
        sg.set_path(port, wwn, 'host0')

    @patch_cli()
    def test_set_path_with_iscsi_port_not_initialized(self):
        def f():
            uid = 'iqn.1992-04.com.abc:a.b.c'
            port = VNXConnectionPort.get(sp=VNXSPEnum.SP_A, port_id=10,
                                         cli=t_cli())[0]
            sg = VNXStorageGroup(cli=t_cli(), name='sg0')
            sg.set_path(port, uid, 'host0')

        assert_that(f, raises(VNXPortNotInitializedError))

    @patch_cli()
    def test_set_path_with_fcoe_port_success(self):
        uid = 'iqn.1992-04.com.abc:a.b.c'
        port = VNXConnectionPort.get(sp=VNXSPEnum.SP_A, port_id=8,
                                     vport_id=0, cli=t_cli())
        sg = VNXStorageGroup(cli=t_cli(), name='sg0')
        # no error raised
        sg.connect_hba(port, uid, 'host0')

    @patch_cli()
    def test_set_path_with_fcoe_already_existed(self):
        def f():
            uid = 'iqn.1992-04.com.abc:a.b.d'
            port = VNXConnectionPort.get(sp=VNXSPEnum.SP_A, port_id=8,
                                         vport_id=0, cli=t_cli())
            sg = VNXStorageGroup(cli=t_cli(), name='sg0')
            sg.set_path(port, uid, 'host0')

        assert_that(f, raises(VNXInitiatorExistedError))
