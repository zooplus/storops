# coding=utf-8
from __future__ import unicode_literals

from past.builtins import filter

from vnxCliApi.lib.common import check_int
from vnxCliApi.vnx.enums import VNXSPEnum, VNXPortType
from vnxCliApi.vnx.resource.resource import VNXCliResourceList, VNXResource

__author__ = 'Cedric Zhuang'


class VNXSPPortList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXSPPort

    def _get_raw_resource(self):
        return self._cli.get_sp_port()


class VNXSPPort(VNXResource):
    def __init__(self, sp=None, port_id=None, cli=None):
        super(VNXSPPort, self).__init__()
        self._cli = cli
        self._sp = sp
        self._port_id = port_id

    def _get_raw_resource(self):
        raise ValueError('Cannot get single sp port info from cli.  '
                         'Use {}.get_port(sp, id, cli) instead.'
                         .format(self.__class__.__name__))

    @classmethod
    def get(cls, cli, sp=None, port_id=None):

        ret = VNXSPPortList(cli)
        if sp is not None:
            ret = filter(lambda p: p.sp == sp, ret)

        if port_id is not None:
            ret = filter(lambda p: p.port_id == port_id, ret)

        if sp is not None and port_id is not None and len(ret) == 1:
            ret = ret[0]

        return ret


class VNXHbaPort(VNXResource):
    @classmethod
    def _get_parser(cls):
        raise ValueError('property not found.')

    def __init__(self, sp, port_id, vport_id=0):
        super(VNXHbaPort, self).__init__()
        self._sp = VNXSPEnum.from_str(sp)
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
        return self._type

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
        if '.' in sg_hba.hba[0]:
            port._type = VNXPortType.ISCSI
        elif ':' in sg_hba.hba[0]:
            port._type = VNXPortType.FC
        port._host_initiator_list.append(sg_hba.hba[0])
        return port

    def as_tuple(self):
        return self.sp, self.port_id

    def __repr__(self):
        return ('<VNXPort {{'
                'sp: {}, '
                'port_id: {}, '
                'vport_id: {}, '
                'host_initiator_list: {}}}>'
                .format(self.sp,
                        self.port_id,
                        self.vport_id,
                        self.host_initiator_list))

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
    @classmethod
    def get_resource_class(cls):
        return VNXConnectionPort

    def _get_raw_resource(self):
        return self._cli.get_connection_port()


class VNXConnectionPort(VNXResource):
    def __init__(self, sp=None, port_id=None, vport_id=None, cli=None):
        super(VNXConnectionPort, self).__init__()
        if sp is None:
            sp = VNXSPEnum.SP_A
        self._sp = sp
        self._port_id = port_id
        self._vport_id = vport_id
        self._cli = cli

    def _get_raw_resource(self):
        return self._cli.get_connection_port(
            sp=self._sp, port_id=self._port_id, vport_id=self._vport_id)

    @classmethod
    def get(cls, cli, sp=None, port_id=None, vport_id=None):
        if sp is not None and port_id is not None and vport_id is not None:
            ret = VNXConnectionPort(sp, port_id, vport_id, cli)
        else:
            ret = VNXConnectionPortList(cli)

            if sp is not None:
                ret = filter(lambda p: p.sp == sp, ret)

            if port_id is not None:
                ret = filter(lambda p: p.port_id == port_id, ret)

            if port_id is not None:
                ret = filter(lambda p: p.virtual_port_id == vport_id,
                             ret)
        return ret
