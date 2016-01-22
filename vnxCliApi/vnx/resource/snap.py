# coding=utf-8
from __future__ import unicode_literals

import six

from vnxCliApi.vnx.cli import raise_if_err
from vnxCliApi.vnx.resource.resource import VNXCliResourceList
from vnxCliApi.vnx.resource.resource import VNXResource
from vnxCliApi import exception as ex

__author__ = 'Cedric Zhuang'


class VNXSnapList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXSnap

    def _get_raw_resource(self):
        return self._cli.get_snap()


class VNXSnap(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXSnap, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_snap(name=self._name)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXSnapList(cli)
        else:
            ret = VNXSnap(name, cli)
        return ret

    def remove(self):
        self._cli.remove_snap(self._get_name())

    def copy(self, new_name,
             ignore_migration_check=False,
             ignore_dedup_check=False):
        name = self._get_name()
        out = self._cli.copy_snap(name, new_name,
                                  ignore_migration_check,
                                  ignore_dedup_check)
        raise_if_err(out, ex.VNXSnapError,
                     'failed to copy snap {}.'.format(name))
        return VNXSnap(name=new_name, cli=self._cli)

    def modify(self, new_name=None, desc=None,
               auto_delete=None, rw=None):
        name = self._get_name()
        out = self._cli.modify_snap(name, new_name, desc, auto_delete, rw)
        raise_if_err(out, ex.VNXSnapError,
                     'failed to modify snap {}.'.format(name))
        if new_name is not None:
            self._name = new_name

    @staticmethod
    def get_name(snap):
        if isinstance(snap, VNXSnap):
            if snap._name is not None:
                ret = snap._name
            else:
                ret = snap.name
        elif isinstance(snap, six.string_types):
            ret = snap
        else:
            raise ValueError('invalid snap.')
        return ret
