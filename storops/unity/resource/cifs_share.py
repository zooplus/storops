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

import storops.unity.resource.cifs_server
import storops.unity.resource.filesystem
from storops.unity.resource import UnityResource, UnityResourceList

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


class UnityCifsShare(UnityResource):
    @classmethod
    def create(cls, cli, name, fs, path=None, cifs_server=None):
        fs_clz = storops.unity.resource.filesystem.UnityFileSystem
        fs = fs_clz.get(cli, fs).verify()
        sr = fs.storage_resource

        if path is None:
            path = '/'

        if cifs_server is None:
            cifs_server = fs.first_available_cifs_server
        else:
            server_clz = storops.unity.resource.cifs_server.UnityCifsServer
            cifs_server = server_clz.get(cli, cifs_server)

        param = cli.make_body(name=name,
                              path=path,
                              cifsServer=cifs_server)
        resp = sr.modify_fs(cifsShareCreate=[param])
        resp.raise_if_err()
        return UnityCifsShareList(cli=cli, name=name).first_item

    def remove(self, async=False):
        fs = self.filesystem.verify()
        sr = fs.storage_resource
        param = self._cli.make_body(cifsShare=self)
        resp = sr.modify_fs(async=async, cifsShareDelete=[param])
        resp.raise_if_err()
        return resp


class UnityCifsShareList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityCifsShare
