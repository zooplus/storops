# coding=utf-8
from __future__ import unicode_literals

import re

from vnxCliApi.lib.common import check_text
from vnxCliApi.vnx.resource.resource import VNXCliResource, VNXCliResourceList

__author__ = 'Cedric Zhuang'


class VNXDisk(VNXCliResource):
    _index_pattern = re.compile('(\w+)_(\w+)_(\w+)')

    def __init__(self, index=None, cli=None):
        super(VNXDisk, self).__init__()
        self._cli = cli
        self._index = index
        if index is not None:
            self.parse_index(self.index)

    @property
    def bus(self):
        return self.parse_index(self._index)[0]

    @property
    def enclosure(self):
        return self.parse_index(self._index)[1]

    @property
    def disk(self):
        return self.parse_index(self._index)[2]

    @property
    def index(self):
        if self._index is None:
            if self.disk_index is not None:
                self._index = '{}_{}_{}'.format(*self.disk_index)
            else:
                raise ValueError('disk index is not initialized.')
        return self._index

    @property
    def index_string(self):
        bus, enc, disk = self.parse_index(self.index)
        return 'bus {} enclosure {} disk {}'.format(bus, enc, disk)

    def _get_raw_resource(self):
        return self._cli.get_disk(poll=self.poll,
                                  *self.parse_index(self._index))

    @classmethod
    def parse_index(cls, index):
        match = re.search(cls._index_pattern, index)
        if match is None:
            raise ValueError('invalid disk index.  disk index must '
                             'be something like '
                             '"1_2_A0", in which "1" is the bus id, "2"'
                             'is the enclosure id and "A0" is the disk id.')
        return match.groups()

    @classmethod
    def get(cls, cli, index=None):
        if index is None:
            ret = VNXDiskList(cli)
        else:
            index = check_text(index).upper()
            ret = VNXDisk(index, cli)
        return ret

    def remove(self):
        return self._cli.remove_disk(self._index, poll=self.poll)

    def install(self):
        return self._cli.install_disk(self._index, poll=self.poll)


class VNXDiskList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXDisk

    def _get_raw_resource(self):
        return self._cli.get_disk(poll=self.poll)
