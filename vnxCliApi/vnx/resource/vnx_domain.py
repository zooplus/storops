# coding=utf-8
from __future__ import unicode_literals

import re

from past.builtins import filter

from vnxCliApi.exception import ObjectNotFound
from vnxCliApi.vnx.enums import VNXSPEnum
from vnxCliApi.vnx.resource.resource import VNXCliResourceList, VNXCliResource

__author__ = 'Cedric Zhuang'


class VNXDomainNodeList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXDomainNode

    def _get_raw_resource(self):
        return self._cli.get_domain(poll=self.poll)

    def get_node(self, node_id):
        for node in self:
            if node.name == node_id:
                ret = node
                break
        else:
            raise ObjectNotFound('domain node "{}" not found'.format(node_id))
        return ret

    @staticmethod
    def get_cs_ip(serial, cli):
        dnl = VNXDomainNodeList(cli)
        dnl.with_no_poll()
        node = dnl.get_node(serial)
        return node.control_station.ip_address


class VNXDomainNode(VNXCliResource):
    @property
    def name(self):
        return self.node

    @property
    def spa(self):
        return self.members.spa

    @property
    def spb(self):
        return self.members.spb

    @property
    def control_station(self):
        return self.members.control_station


class VNXDomainMemberList(VNXCliResourceList):
    def _get_member(self, index):
        def filter_by_sp_name(member):
            sp = VNXSPEnum.from_str(member.name)
            return sp == index

        result = filter(filter_by_sp_name, self.list)
        ret = None
        if len(result) > 0:
            ret = result[0]
        return ret

    @property
    def spa(self):
        return self._get_member(VNXSPEnum.SP_A)

    @property
    def spb(self):
        return self._get_member(VNXSPEnum.SP_B)

    @property
    def control_station(self):
        return self._get_member(VNXSPEnum.CONTROL_STATION)

    @classmethod
    def get_resource_class(cls):
        return VNXDomainMember

    def _get_raw_resource(self):
        raise NotImplementedError('cli does not support list domain member'
                                  'of a specified node.  '
                                  'please use VNXDomainNode instead.')


class VNXDomainMember(VNXCliResource):
    @property
    def ip(self):
        ret = 'N/A'
        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', self.ip_address)
        if len(ip) > 0:
            ret = ip[0]
        return ret

    @property
    def is_master(self):
        return 'Master' in self.ip_address


class VNXNetworkAdmin(VNXCliResource):
    def __init__(self, sp_index, cli):
        super(VNXNetworkAdmin, self).__init__()
        self._cli = cli
        self._sp = VNXSPEnum.from_str(sp_index)

    def _get_raw_resource(self):
        return self._cli.sp_network_status(self._sp, poll=self.poll)

    @staticmethod
    def _get_sp_ip(sp, cli):
        sp = VNXNetworkAdmin(VNXSPEnum.from_str(sp), cli)
        sp.with_no_poll()
        return sp.ip

    @classmethod
    def get_spa_ip(cls, cli):
        return cls._get_sp_ip(VNXSPEnum.SP_A, cli)

    @classmethod
    def get_spb_ip(cls, cli):
        return cls._get_sp_ip(VNXSPEnum.SP_B, cli)
