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
import threading
from time import sleep

import filelock
from retryz import retry

from collections import defaultdict

from comptest import t_vnx
from storops import exception as ex
from test.utils import PersistedDict

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class VNXTestResourceManager(object):
    def __init__(self, name):
        self._names = self._init_names()
        self._name = name
        self._add_worker()
        self.vnx = None

    def _init_names(self):
        return defaultdict(list)

    def _add_worker(self):
        workers = self._names['worker']
        _id = threading.current_thread().ident
        if _id not in workers:
            workers.append(_id)
        self._names['worker'] = workers

    def _remove_worker(self):
        workers = self._names['worker']
        _id = threading.current_thread().ident
        if _id in workers:
            workers.remove(_id)
        self._names['worker'] = workers
        return len(workers)

    def clean_up(self):
        while self._remove_worker():
            # wait for all test cases to complete
            sleep(5)

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

    def has_snap_name(self, name=None):
        return self.has_name('snap', name)

    def has_lun_name(self, name=None):
        return self.has_name('lun', name)

    def has_pool_name(self, name=None):
        return self.has_name('pool', name)

    def add_snap_name(self, name=None):
        return self.add_name('snap', name)

    def add_lun_name(self, name=None):
        return self.add_name('lun', name)

    def add_pool_name(self, name=None):
        return self.add_name('pool', name)

    def has_name(self, rsc_type, key=None):
        names = self._names[rsc_type]
        if names:
            if key is None:
                ret = True
            else:
                ret = key in names
        else:
            ret = False
        return ret

    def _pop_name(self, rsc_type):
        names = self._names[rsc_type]
        ret = names.pop()
        self._names[rsc_type] = names
        return ret

    def add_name(self, rsc_type, name=None):
        names = self._names[rsc_type]
        n = len(names)

        if name is None:
            name = '{}_{}_{}'.format(self._name, rsc_type, n)
        names.append(name)
        self._names[rsc_type] = names
        return name


class VNXGeneralFixtureManager(VNXTestResourceManager):
    def __init__(self):
        clz_name = self.__class__.__name__
        file_lock_name = '{}.lck'.format(clz_name)
        self.lock = filelock.FileLock(file_lock_name)
        with self.lock.acquire():
            log.debug('start {} setup.'.format(clz_name))
            # noinspection PyBroadException
            try:
                super(VNXGeneralFixtureManager, self).__init__('general')
                self.vnx = t_vnx()
                self.pool = self._create_pool()
                self.lun = self._create_lun()
                self.snap = self._create_snap()
            except Exception:
                log.exception(
                    'failed to initialize {}'.format(clz_name))

    def _init_names(self):
        data_file = '{}_names'.format(self.__class__.__name__)
        return PersistedDict(data_file, list)

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
