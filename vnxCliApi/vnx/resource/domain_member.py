# coding=utf-8
from __future__ import unicode_literals

import re

from past.builtins import filter

from vnxCliApi.vnx.enums import VNXSPEnum
from vnxCliApi.vnx.resource.resource import VNXCliResourceList, VNXResource

__author__ = 'Cedric Zhuang'


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
        return self._cli.get_domain()


class VNXDomainMember(VNXResource):
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
