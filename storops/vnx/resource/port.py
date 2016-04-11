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

from storops.exception import raise_if_err
from storops.lib.common import check_int
from storops.vnx.enums import VNXSPEnum, VNXPortType
from storops.vnx.resource import VNXCliResourceList, VNXCliResource

__author__ = 'Cedric Zhuang'


class VNXSPPortList(VNXCliResourceList):
    def __init__(self, cli, sp=None, port_id=None, port_type=None):
        super(VNXSPPortList, self).__init__(cli=cli)
        self._sp = sp
        self._port_id = port_id
        self._port_type = port_type

    def _filter(self, item):
        ret = True

        if self._sp is not None:
            ret &= item.sp == self._sp

        if self._port_id is not None:
            ret &= item.port_id == self._port_id

        if self._port_type is not None:
            ret &= item.type == self._port_type

        return ret

    @classmethod
    def get_resource_class(cls):
        return VNXSPPort

    def _get_raw_resource(self):
        return self._cli.get_sp_port(poll=self.poll)


class VNXSPPort(VNXCliResource):
    def __init__(self, sp=None, port_id=None, cli=None):
        super(VNXSPPort, self).__init__()
        self._cli = cli
        self._sp = sp
        self._port_id = port_id

    def _get_raw_resource(self):
        raise ValueError('Cannot get single sp port info from cli.  '
                         'Use {}.get(sp, port_id, cli) instead.'
                         .format(self.__class__.__name__))

    @classmethod
    def get(cls, cli, sp=None, port_id=None, port_type=None):
        ret = VNXSPPortList(cli, sp=sp, port_id=port_id, port_type=port_type)
        if sp is not None and port_id is not None and len(ret) == 1:
            ret = ret[0]
        return ret

    @property
    def type(self):
        return VNXPortType.parse(self.wwn)

    def property_names(self):
        ret = super(VNXSPPort, self).property_names()
        ret.append('type')
        return ret

    @classmethod
    def remove_hba(cls, cli, hba_uid):
        out = cli.remove_hba(hba_uid)
        raise_if_err(out)


class VNXHbaPort(VNXCliResource):
    @classmethod
    def _get_parser(cls):
        raise ValueError('property not found.')

    def __init__(self, sp, port_id, vport_id=0):
        super(VNXHbaPort, self).__init__()
        self._sp = VNXSPEnum.parse(sp)
        self._port_id = check_int(port_id)
        self._vport_id = check_int(vport_id)
        self._type = VNXPortType.FC
        self._host_initiator_list = []

    def is_valid(self):
        return self.sp is not None and self.port_id is not None

    @property
    def sp(self):
        return self._sp

    def get_sp_index(self):
        return VNXSPEnum.get_sp_index(self.sp)

    @property
    def port_id(self):
        return self._port_id

    @property
    def vport_id(self):
        return self._vport_id

    @property
    def type(self):
        ret = None
        if self.host_initiator_list:
            ret = VNXPortType.parse(self.host_initiator_list[0])
        return ret

    @property
    def host_initiator_list(self):
        return tuple(self._host_initiator_list)

    @staticmethod
    def create(sp, port_id, port_type=VNXPortType.FC, vport_id=0):
        port = VNXHbaPort(sp, port_id, vport_id)
        port._type = port_type
        return port

    @staticmethod
    def from_storage_group_hba(sg_hba):
        port = VNXHbaPort.create(sg_hba.sp, sg_hba.port_id,
                                 vport_id=sg_hba.vlan)
        port._host_initiator_list.append(sg_hba.hba[0])
        return port

    def as_tuple(self):
        return self.sp, self.port_id

    def get_index(self):
        return 'sp'

    def property_names(self):
        return ['sp', 'port_id', 'vport_id', 'type',
                'host_initiator_list']

    def __hash__(self):
        return hash('<VNXPort {{'
                    'sp: {}, '
                    'port_id: {}, '
                    'vport_id: {}}}'
                    .format(self.sp,
                            self.port_id,
                            self.vport_id))

    def __eq__(self, other):
        return self.sp == other.sp and self.port_id == other.port_id


class VNXConnectionPortList(VNXCliResourceList):
    def __init__(self, cli, sp=None, port_id=None, vport_id=None,
                 port_type=None):
        super(VNXConnectionPortList, self).__init__(cli=cli)
        self._sp = sp
        self._port_id = port_id
        self._vport_id = vport_id
        self._port_type = port_type

    def _filter(self, item):
        ret = True
        if self._sp is not None:
            ret &= item.sp == self._sp

        if self._port_id is not None:
            ret &= item.port_id == self._port_id

        if self._vport_id is not None:
            ret = item.virtual_port_id == self._vport_id

        if self._port_type is not None:
            ret &= item.type == self._port_type
        return ret

    @classmethod
    def get_resource_class(cls):
        return VNXConnectionPort

    def _get_raw_resource(self):
        return self._cli.get_connection_port(poll=self.poll)


class VNXConnectionPort(VNXCliResource):
    def __init__(self, sp=None, port_id=None, vport_id=None, cli=None):
        super(VNXConnectionPort, self).__init__()
        if sp is None:
            sp = VNXSPEnum.SP_A
        self._sp = sp
        self._port_id = port_id
        self._vport_id = vport_id
        self._cli = cli

    @property
    def type(self):
        ret = VNXPortType.parse(self.wwn)
        if ret == VNXPortType.FC and self.virtual_port_id is not None:
            ret = VNXPortType.FCOE
        return ret

    def _get_raw_resource(self):
        return self._cli.get_connection_port(
            sp=self._sp, port_id=self._port_id, vport_id=self._vport_id,
            poll=self.poll)

    def property_names(self):
        names = super(VNXConnectionPort, self).property_names()
        names.append('type')
        return names

    @classmethod
    def get(cls, cli, sp=None, port_id=None, vport_id=None, port_type=None):
        VNXPortType.verify(port_type)
        if sp is not None and port_id is not None and vport_id is not None:
            ret = VNXConnectionPort(sp, port_id, vport_id, cli)
        else:
            ret = VNXConnectionPortList(cli, sp, port_id, vport_id, port_type)
        return ret
