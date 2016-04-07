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
import storops.unity.resource.snap
from storops.lib.common import instance_cache
from storops.unity.enums import CIFSTypeEnum, ACEAccessTypeEnum, \
    ACEAccessLevelEnum
from storops.unity.resource import UnityResource, UnityResourceList, \
    UnityAttributeResource

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

    @classmethod
    def create_from_snap(cls, cli, snap, name, path=None, is_read_only=None):
        snap_clz = storops.unity.resource.snap.UnitySnap
        snap = snap_clz.get(cli, snap)

        if path is None:
            path = '/'

        resp = cli.post(cls().resource_class,
                        snap=snap,
                        path=path,
                        name=name,
                        isReadOnly=is_read_only)
        resp.raise_if_err()
        return cls(_id=resp.resource_id, cli=cli)

    @property
    @instance_cache
    def storage_resource(self):
        fs = self.filesystem
        if fs is not None:
            ret = fs.storage_resource
        else:
            ret = None
        return ret

    def remove(self, async=False):
        if self.type == CIFSTypeEnum.CIFS_SNAPSHOT:
            resp = super(UnityCifsShare, self).remove(async=async)
        else:
            fs = self.filesystem.verify()
            sr = fs.storage_resource
            param = self._cli.make_body(cifsShare=self)
            resp = sr.modify_fs(async=async, cifsShareDelete=[param])
        resp.raise_if_err()
        return resp

    def get_ace_list(self):
        resp = self.action('getACEs')
        resp.raise_if_err()

    def enable_ace(self):
        return self.modify(is_ace_enabled=True)

    def disable_ace(self):
        return self.modify(is_ace_enabled=False)

    def add_ace(self, domain, user, access_level=None):
        if access_level is None:
            access_level = ACEAccessLevelEnum.FULL
        sid = UnityAclUser.get_sid(self._cli, user=user, domain=domain)
        ace = self._cli.make_body(
            sid=sid,
            accessType=ACEAccessTypeEnum.GRANT,
            accessLevel=access_level
        )

        resp = self.modify(add_ace=[ace])
        resp.raise_if_err()
        return resp

    def modify(self, is_read_only=None, is_ace_enabled=None, add_ace=None,
               delete_ace=None):
        sr = self.storage_resource
        if sr is None:
            raise ValueError('storage resource for share {} not found.'
                             .format(self.name))

        share_param = self._cli.make_body(
            allow_empty=True,
            isReadOnly=is_read_only,
            isACEEnabled=is_ace_enabled,
            addACE=add_ace,
            deleteAce=delete_ace)
        modify_param = self._cli.make_body(
            allow_empty=True,
            cifsShare=self,
            cifsShareParameters=share_param)
        param = self._cli.make_body(
            allow_empty=True,
            cifsShareModify=[modify_param])

        resp = sr.modify_fs(**param)
        resp.raise_if_err()
        return resp


class UnityCifsShareList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityCifsShare


class UnityCifsShareAce(UnityAttributeResource):
    pass


class UnityCifsShareAceList(UnityResourceList):
    def sid_list(self):
        return [ace.sid for ace in self]

    @classmethod
    def get_resource_class(cls):
        return UnityCifsShareAce


class UnityAclUser(UnityResource):
    @classmethod
    def get_sid(cls, cli, user, domain):
        resp = cli.type_action(cls().resource_class,
                               'lookupSIDByDomainUser',
                               domainName=domain,
                               userName=user)
        resp.raise_if_err()
        return resp.first_content.get('sid')


class UnityAclUserList(UnityResourceList):
    @classmethod
    def get_resource_class(cls):
        return UnityAclUser
