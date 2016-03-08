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
from storops.exception import UnityResourceNotFoundError
from storops.unity.enums import FSSupportedProtocolEnum, TieringPolicyEnum

import storops.unity.resource.nas_server
import storops.unity.resource.pool
import storops.unity.resource.nfs_share
import storops.unity.resource.cifs_share
from storops.unity.resource import UnityResource, UnityResourceList
from storops.unity.resource.storage_resource import UnityStorageResource

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


class UnityFileSystem(UnityResource):
    @classmethod
    def create(cls, cli, pool, nas_server, name, size,
               proto=None, is_thin=None,
               tiering_policy=None):
        pool_clz = storops.unity.resource.pool.UnityPool
        nas_server_clz = storops.unity.resource.nas_server.UnityNasServer

        if proto is None:
            proto = FSSupportedProtocolEnum.NFS

        pool = pool_clz.get(cli, pool)
        nas_server = nas_server_clz.get(cli, nas_server)
        FSSupportedProtocolEnum.verify(proto)
        TieringPolicyEnum.verify(tiering_policy)

        req_body = {
            'name': name,
            'fsParameters': {
                'pool': pool,
                'nasServer': nas_server,
                'supportedProtocols': proto,
                'isThinEnabled': is_thin,
                'size': size,
                'fastVPParameters': {
                    'tieringPolicy': tiering_policy
                }
            },
        }
        resp = cli.type_action(UnityStorageResource().resource_class,
                               'createFilesystem',
                               **req_body)
        resp.raise_if_err()
        sr = UnityStorageResource(_id=resp.resource_id, cli=cli)
        return sr.filesystem

    @property
    def first_available_cifs_server(self):
        ret = None
        if self.nas_server is not None:
            cifs_servers = self.nas_server.cifs_server
            if cifs_servers:
                ret = cifs_servers[0]
        return ret

    def remove(self, force_snap_delete=False, force_vvol_delete=False,
               async=False):
        sr = self.storage_resource
        if not self.existed or sr is None:
            raise UnityResourceNotFoundError(
                'cannot find filesystem {}.'.format(self.get_id()))
        resp = self._cli.delete(sr.resource_class,
                                sr.get_id(),
                                forceSnapDeletion=force_snap_delete,
                                forceVvolDeletion=force_vvol_delete,
                                async=async)
        resp.raise_if_err()
        return resp

    def extend(self, new_size):
        sr = self.storage_resource
        param = self._cli.make_body(size=new_size)
        resp = sr.modify_fs(fsParameters=param)
        resp.raise_if_err()
        return resp

    def create_nfs_share(self, name, path=None, share_access=None):
        clz = storops.unity.resource.nfs_share.UnityNfsShare
        return clz.create(self._cli, name=name, fs=self,
                          path=path, share_access=share_access)

    def create_cifs_share(self, name, path=None, cifs_server=None):
        clz = storops.unity.resource.cifs_share.UnityCifsShare
        return clz.create(self._cli, name=name, fs=self,
                          path=path, cifs_server=cifs_server)


class UnityFileSystemList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityFileSystem
