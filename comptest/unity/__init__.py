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

from comptest import t_unity
from comptest.utils import ResourceManager
from storops import exception as ex, FSSupportedProtocolEnum

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class UnityTestResourceManager(ResourceManager):
    def __init__(self, name):
        super(UnityTestResourceManager, self).__init__(name)
        self.unity = None

    def clean_up(self):
        super(UnityTestResourceManager, self).clean_up()

        self._clean_up_snap()
        self._clean_up_cifs_share()
        self._clean_up_nfs_share()
        self._clean_up_fs()
        self._clean_up_nas_server()

        self._names.destroy()

    def _clean_up_nas_server(self):
        while self.has_nas_server_name():
            name = None
            try:
                name = self._pop_name('nas_server')
                server = self.unity.get_nas_server(name=name)
                if server.existed:
                    self._delete_nas_server(server)
            except ex.UnityResourceNotFoundError:
                log.exception('remove nas server {} failed.'.format(name))

    def _clean_up_fs(self):
        while self.has_fs_name():
            name = None
            try:
                name = self._pop_name('fs')
                fs = self.unity.get_filesystem(name=name)
                if fs.existed:
                    fs.delete(force_snap_delete=True,
                              force_vvol_delete=True)
            except ex.UnityResourceNotFoundError:
                log.exception('remove fs {} failed.'.format(name))

    def _clean_up_nfs_share(self):
        while self.has_nfs_share_name():
            self._pop_name('nfs_share')

    def _clean_up_cifs_share(self):
        while self.has_cifs_share_name():
            self._pop_name('cifs_share')

    def _clean_up_snap(self):
        while self.has_snap_name():
            self._pop_name('snap')

    @retry(on_error=ex.UnityNasServerHasFsError, wait=7)
    def _delete_nas_server(self, server):
        server.delete()


class UnityGeneralFixtureManager(UnityTestResourceManager):
    def __init__(self):
        clz_name = self.__class__.__name__
        log.debug('start {} setup.'.format(clz_name))
        # noinspection PyBroadException
        try:
            super(UnityGeneralFixtureManager, self).__init__('general')
            self.unity = t_unity()
            self.pool = self._create_pool()
            self.nas_server = self._create_nas_server()

            self._enable_nfs_service()
            self._enable_cifs_service()

            self.cifs_share = self._create_cifs_share()
            self.nfs_share = self._create_nfs_share()
        except Exception:
            log.exception(
                'failed to initialize {}'.format(clz_name))
            raise

    def _create_pool(self):
        return self.unity.get_pool(_id='pool_1')

    def _create_nas_server(self):
        name = 'general_nas_server'
        try:
            server = self.unity.create_nas_server(name)
            self.add_nas_server_name(name)
        except ex.UnityNasServerNameUsedError:
            server = self.unity.get_nas_server(name=name)

        return server

    def _create_fs(self, name, proto):
        size = 3 * 1024 ** 3
        try:
            fs = self.pool.create_filesystem(self.nas_server, name, size,
                                             proto=proto)
            self.add_fs_name(name)
        except ex.UnityFileSystemNameAlreadyExisted:
            fs = self.unity.get_filesystem(name=name)
        return fs

    def _create_cifs_share(self):
        fs_name = 'general_fs_cifs_share'
        fs = self._create_fs(fs_name, proto=FSSupportedProtocolEnum.CIFS)
        name = 'general_cifs_share'
        try:
            cs = fs.create_cifs_share(name=name)
            self.add_cifs_share_name(name)
        except (ex.UnitySmbShareNameExistedError, ex.UnitySmbNameInUseError):
            cs = self.unity.get_cifs_share(name=name)
        return cs

    def _create_nfs_share(self):
        fs_name = 'general_fs_nfs_share'
        fs = self._create_fs(fs_name, proto=FSSupportedProtocolEnum.NFS)
        name = 'general_nfs_share'
        try:
            ns = fs.create_nfs_share(name=name)
            self.add_nfs_share_name(name)
        except ex.UnityNfsShareNameExistedError:
            ns = self.unity.get_nfs_share(name=name)
        return ns

    def _enable_nfs_service(self):
        try:
            self.nas_server.enable_nfs_service()
        except ex.UnityNfsAlreadyEnabledError:
            log.info('nfs already enabled on {}'.format(self.nas_server.name))

    def _enable_cifs_service(self):
        try:
            self.nas_server.enable_cifs_service(
                name='unity_ct',
                workgroup='UNITY_CT_GROUP',
                local_password='Password123!')
        except ex.UnityNetBiosNameExistedError:
            log.info('cifs already enabled on {}'.format(self.nas_server.name))
