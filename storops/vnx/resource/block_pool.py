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

from storops.lib.common import instance_cache
from storops.vnx.resource import VNXCliResource, VNXCliResourceList
from storops.vnx.resource.lun import VNXLun, VNXLunList
from storops import exception as ex

__author__ = 'Cedric Zhuang'


class VNXPoolFeature(VNXCliResource):
    def __init__(self, cli=None):
        super(VNXPoolFeature, self).__init__()
        self._cli = cli

    def _get_raw_resource(self):
        return self._cli.get_pool_feature(poll=self.poll)


class VNXPoolList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXPool

    def _get_raw_resource(self):
        return self._cli.get_pool(poll=self.poll)


class VNXPool(VNXCliResource):
    def __init__(self, pool_id=None, name=None, cli=None):
        super(VNXPool, self).__init__()
        self._cli = cli
        self._pool_id = pool_id
        self._name = name

    def _get_pool_id(self):
        if self._pool_id is not None:
            ret = self._pool_id
        else:
            ret = self.pool_id
        return ret

    def _get_name_or_id(self):
        ret = {'name': None, 'pool_id': None}
        if self._pool_id is not None:
            ret['pool_id'] = self._pool_id
        else:
            ret['name'] = self._get_name()
        return ret

    def __setattr__(self, key, value):
        if key == 'name':
            self.rename(value)
            return
        super(VNXPool, self).__setattr__(key, value)

    def rename(self, new_name):
        if new_name is not None and new_name != self._name:
            ret = self._cli.modify_storage_pool(new_name=new_name,
                                                poll=self.poll,
                                                **self._get_name_or_id())
            ex.raise_if_err(ret, default=ex.VNXModifyPoolError)
            self._name = new_name

    @staticmethod
    def create(cli, name, disks, raid_type=None, ):
        ret = cli.create_pool(name, disks, raid_type)
        ex.raise_if_err(ret, default=ex.VNXCreatePoolError)
        return VNXPool(name=name, cli=cli)

    def remove(self):
        ret = self._cli.remove_pool(poll=self.poll, **self._get_name_or_id())
        ex.raise_if_err(ret, default=ex.VNXRemovePoolError)

    @classmethod
    def get(cls, cli, pool_id=None, name=None):
        if pool_id is None and name is None:
            ret = VNXPoolList(cli)
        else:
            ret = VNXPool(pool_id, name, cli)
        return ret

    def create_lun(self,
                   lun_name=None,
                   size_gb=1,
                   lun_id=None,
                   provision=None,
                   tier=None,
                   ignore_thresholds=None):
        pool = {}
        if self._pool_id is not None:
            pool['pool_id'] = self._pool_id
        else:
            pool['pool_name'] = self._get_name()
        ret = self._cli.create_pool_lun(
            lun_name=lun_name,
            lun_id=lun_id,
            size_gb=size_gb,
            provision=provision,
            tier=tier,
            ignore_thresholds=ignore_thresholds,
            poll=self.poll,
            **pool)
        ex.raise_if_err(ret, 'error creating lun.',
                        default=ex.VNXCreateLunError)
        return VNXLun(lun_id, lun_name, self._cli)

    @staticmethod
    def remove_lun(lun, remove_snapshots=False, force_detach=False):
        lun.remove(remove_snapshots, force_detach)

    def _get_raw_resource(self):
        return self._cli.get_pool(poll=self.poll, **self._get_name_or_id())

    @instance_cache
    def get_lun(self):
        return VNXLunList(self._cli, pool=self)

    @property
    def lun_list(self):
        return self.get_lun()
