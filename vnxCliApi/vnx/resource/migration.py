# coding=utf-8
from __future__ import unicode_literals

import vnxCliApi.vnx.resource.lun
from vnxCliApi.vnx.resource.resource import VNXCliResourceList, VNXCliResource

__author__ = 'Cedric Zhuang'


class VNXMigrationSessionList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXMigrationSession

    def _get_raw_resource(self):
        return self._cli.get_migration_session(poll=self.poll)


class VNXMigrationSession(VNXCliResource):
    def __init__(self, source=None, cli=None):
        super(VNXMigrationSession, self).__init__()
        self._cli = cli
        self._source = source

    def _get_raw_resource(self):
        source_id = vnxCliApi.vnx.resource.lun.VNXLun.get_id(self._source)
        return self._cli.get_migration_session(source_id, poll=self.poll)

    @classmethod
    def get(cls, cli, source=None):
        if source is None:
            ret = VNXMigrationSessionList(cli)
        else:
            ret = VNXMigrationSession(source, cli)
        return ret
