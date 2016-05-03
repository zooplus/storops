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

import logging

from retryz import retry

from comptest import t_vnx
from comptest.utils import ResourceManager
from storops import exception as ex

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class VNXTestResourceManager(ResourceManager):
    def __init__(self, name):
        super(VNXTestResourceManager, self).__init__(name)
        self.vnx = None

    def clean_up(self):
        super(VNXTestResourceManager, self).clean_up()

        while self.has_snap_name():
            self._pop_name('snap')

        while self.has_name('lun'):
            name = None
            try:
                name = self._pop_name('lun')
                lun = self.vnx.get_lun(name=name)
                if lun.existed:
                    lun.delete(force=True)
            except (ex.VNXLunNotFoundError, ex.VNXDeleteLunError, IndexError):
                log.exception('remove lun {} failed.'.format(name))

        while self.has_name('pool'):
            name = None
            try:
                name = self._pop_name('pool')
                pool = self.vnx.get_pool(name=name)
                if pool.existed:
                    pool.delete(force=True)
            except (ex.VNXPoolNotFoundError, ex.VNXPoolDestroyingError,
                    IndexError):
                log.exception('remove pool {} failed.'.format(name))

        self._names.destroy()


class VNXGeneralFixtureManager(VNXTestResourceManager):
    def __init__(self):
        clz_name = self.__class__.__name__
        log.debug('start {} setup.'.format(clz_name))
        # noinspection PyBroadException
        try:
            super(VNXGeneralFixtureManager, self).__init__('general')
            self.vnx = t_vnx()
            self.pool = self._create_pool()
            self.lun = self._create_lun()
            self.snap = self._create_snap()
        except Exception:
            log.exception('failed to initialize {}'.format(clz_name))

    def _create_snap(self):
        name = 'general_snap'
        if not self.has_snap_name(name):

            @retry(on_error=ex.VNXLunPreparingError, wait=7)
            def _do_create():
                try:
                    snap = self.lun.create_snap(name, allow_rw=True)
                except ex.VNXSnapNameInUseError:
                    snap = self.vnx.get_snap(name)
                self.add_snap_name(name)
                return snap

            ret = _do_create()
        else:
            ret = self.vnx.get_snap(name)
        return ret

    def _create_pool(self):
        name = 'general_pool'
        if not self.has_pool_name(name):

            @retry(on_error=ex.VNXDiskUsedError, wait=7)
            def _do_create():
                try:
                    pool = self.vnx.create_pool(name)
                except ex.VNXPoolNameInUseError:
                    pool = self.vnx.get_pool(name=name)
                self.add_pool_name(name)
                return pool

            ret = _do_create()
        else:
            ret = self.vnx.get_pool(name=name)
        return ret

    def _create_lun(self):
        name = 'general_lun'
        if not self.has_lun_name(name):
            try:
                ret = self.pool.create_lun(name)
            except ex.VNXLunNameInUseError:
                ret = self.vnx.get_lun(name=name)
            self.add_lun_name(name)
        else:
            ret = self.vnx.get_lun(name=name)
        return ret
