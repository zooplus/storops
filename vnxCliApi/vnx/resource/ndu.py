# coding=utf-8
from __future__ import unicode_literals

from vnxCliApi.vnx.resource.resource import VNXCliResourceList
from vnxCliApi.vnx.resource.resource import VNXCliResource

__author__ = 'Cedric Zhuang'


class VNXNduList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXNdu

    def _get_raw_resource(self):
        return self._cli.get_ndu(poll=self.poll)


class VNXNdu(VNXCliResource):
    def __init__(self, name=None, cli=None):
        super(VNXNdu, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_ndu(name=self._name, poll=self.poll)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXNduList(cli)
        else:
            ret = VNXNdu(name, cli)
        return ret
