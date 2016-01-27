# coding=utf-8
from __future__ import unicode_literals

from vnxCliApi.vnx.cli import raise_if_err
from vnxCliApi.vnx.resource.resource import VNXCliResource, VNXCliResourceList
from vnxCliApi import exception as ex

__author__ = 'Cedric Zhuang'


class VNXRaidGroup(VNXCliResource):
    def __init__(self, raid_group_id=None, cli=None):
        super(VNXRaidGroup, self).__init__()
        self._cli = cli
        self._raid_group_id = raid_group_id

    def _get_raid_group_id(self):
        if self._raid_group_id is not None:
            ret = self._raid_group_id
        else:
            ret = self.raid_group_id
        return ret

    def _get_raw_resource(self):
        return self._cli.get_rg(rg_id=self._raid_group_id, poll=self.poll)

    @staticmethod
    def create(cli, raid_group_id, disks, raid_type=None):
        ret = cli.create_rg(disks, raid_group_id, raid_type)
        raise_if_err(ret, ex.VNXCreateRaidGroupError)
        return VNXRaidGroup(raid_group_id, cli)

    def remove(self):
        ret = self._cli.remove_rg(self._get_raid_group_id(), poll=self.poll)
        raise_if_err(ret, ex.VNXRemoveRaidGroupError)

    @classmethod
    def get(cls, cli, raid_group_id=None):
        if raid_group_id is None:
            ret = VNXRaidGroupList(cli)
        else:
            ret = VNXRaidGroup(raid_group_id, cli)
        return ret


class VNXRaidGroupList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXRaidGroup

    def _get_raw_resource(self):
        return self._cli.get_rg(poll=self.poll)
