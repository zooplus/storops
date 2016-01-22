# coding=utf-8
from __future__ import unicode_literals

from vnxCliApi.vnx.cli import raise_if_err
from vnxCliApi.vnx.resource.lun import VNXLun
from vnxCliApi.vnx.resource.resource import VNXResource, VNXCliResourceList
from vnxCliApi import exception as ex

__author__ = 'Cedric Zhuang'


class VNXConsistencyGroupList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXConsistencyGroup

    def _get_raw_resource(self):
        return self._cli.get_cg()


class VNXConsistencyGroup(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXConsistencyGroup, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_cg(name=self._name)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXConsistencyGroupList(cli)
        else:
            ret = VNXConsistencyGroup(name, cli)
        return ret

    @classmethod
    def create(cls, cli, name, members=None, auto_delete=None):
        cli.create_cg(name, members, auto_delete)
        return VNXConsistencyGroup(name=name, cli=cli)

    def remove(self):
        name = self._get_name()
        out = self._cli.remove_cg(name)
        raise_if_err(out, ex.VNXConsistencyGroupError,
                     'error remove cg "{}".'.format(name))

    def _cg_member_op(self, op, lun_list):
        id_list = VNXLun.get_id_list(*lun_list)
        name = self._get_name()
        out = op(name, *id_list)
        raise_if_err(out, ex.VNXConsistencyGroupError,
                     'error change member of "{}".'.format(name))

    def add_member(self, *lun_list):
        self._cg_member_op(self._cli.add_cg_member, lun_list)

    def remove_member(self, *lun_list):
        self._cg_member_op(self._cli.remove_cg_member, lun_list)

    def replace_member(self, *lun_list):
        self._cg_member_op(self._cli.replace_cg_member, lun_list)
