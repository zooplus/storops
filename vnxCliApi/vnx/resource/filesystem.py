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
import re

import six
from retryz import retry

from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXInvalidMoverID, VNXBackendError, \
    ObjectNotFound
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


class VNXFileSystem(file_resource.Resource):
    def delete(self):
        self.manager.delete(self.name)

    def extend(self, new_size, pool_name=None):
        if pool_name:
            self.manager.extend(self.name, new_size, pool_name=pool_name)
        else:
            self.manager.extend(self.name, new_size, pool_id=self.pools[0])


class FileSystemManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = VNXFileSystem

    def __init__(self, manager):
        super(FileSystemManager, self).__init__(manager)
        self.filesystem_map = dict()

    @retry(on_error=VNXInvalidMoverID)
    def create(self, name, size, pool_name, mover_name, is_vdm=True):
        pool_manager = self.manager.get_object_manager('pool')
        pool = pool_manager.get(pool_name)

        mover = self._get_mover(mover_name, is_vdm)
        if is_vdm:
            mover_builder = self.xml_builder.Vdm(vdm=mover.id)
        else:
            mover_builder = self.xml_builder.Mover(mover=mover.id)

        request = self._build_task_package(
            self.xml_builder.NewFileSystem(
                mover_builder,
                self.xml_builder.StoragePool(
                    pool=pool.id,
                    size=six.text_type(size),
                    mayContainSlices='true'
                ),
                name=name
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._response_validation(response,
                                       constants.MSG_FILESYSTEM_EXIST):
            LOG.warn("File system %s already exists. Skip the creation.",
                     name)
        elif constants.STATUS_OK != response['maxSeverity']:
            message = (("Failed to create file system %(name)s. "
                        "Reason: %(err)s.") %
                       {'name': name, 'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)

        filesystem = {
            'name': name,
            'volumeSize': size,
        }

        self.filesystem_map[name] = self.resource_class(self, filesystem)

        return self.filesystem_map[name]

    def get(self, name):
        if self._cache_missed(name, self.filesystem_map):
            request = self._build_query_package(
                self.xml_builder.FileSystemQueryParams(
                    self.xml_builder.AspectSelection(
                        fileSystems='true',
                        fileSystemCapacityInfos='true'
                    ),
                    self.xml_builder.Alias(name=name)
                )
            )

            response = self._send_request(request)

            if constants.STATUS_OK != response['maxSeverity']:
                if self._is_filesystem_nonexistent(response):
                    message = (("No fileSystem is available. "
                                "Status: %(status)s, Reason: %(err)s.") %
                               {'status': response['maxSeverity'],
                                'err': response['problems']})
                    LOG.error(message)
                    raise ObjectNotFound(err=message)
                else:
                    message = (("Failed to get filesystem information. "
                                "Status: %(status)s, Reason: %(err)s.") %
                               {'status': response['maxSeverity'],
                                'err': response['problems']})
                    LOG.error(message)
                    raise VNXBackendError(err=message)

            if not response['objects']:
                message = (("No fileSystem is available. "
                            "Status: %(status)s, Reason: %(err)s.") %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                LOG.error(message)
                raise ObjectNotFound(err=message)

            filesystem = response['objects'][0]
            if name not in self.filesystem_map:
                self.filesystem_map[name] = self.resource_class(
                    self, filesystem, loaded=True)
            else:
                self.filesystem_map[name].update(filesystem)

        return self.filesystem_map[name]

    def _is_filesystem_nonexistent(self, response):
        """Check filesystem exist or not."""
        msg_codes = self._get_problem_message_codes(response['problems'])
        diags = self._get_problem_diags(response['problems'])

        for code, diagnose in zip(msg_codes, diags):
            if (code == constants.MSG_FILESYSTEM_NOT_FOUND and
                    diagnose.find('File system not found.') != -1):
                return True

        return False

    def delete(self, name):
        try:
            filesystem = self.get(name)
        except ObjectNotFound:
            LOG.warn("File system %s not found. Skip the deletion.",
                     name)
            return
        except VNXBackendError as ex:
            message = (("Failed to get file system by name %(name)s. "
                        "Reason: %(err)s.") %
                       {'name': name, 'err': ex})
            LOG.error(message)
            raise ex

        request = self._build_task_package(
            self.xml_builder.DeleteFileSystem(fileSystem=filesystem.id)
        )

        response = self._send_request(request)

        if constants.STATUS_OK != response['maxSeverity']:
            message = (("Failed to delete file system %(name)s. "
                        "Reason: %(err)s.") %
                       {'name': name, 'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)

        if name in self.filesystem_map:
            self.filesystem_map.pop(name)

    def extend(self, name, new_size, pool_name=None, pool_id=None):
        try:
            filesystem = self.get(name)
        except ObjectNotFound or VNXBackendError as ex:
            message = (("Failed to get file system by name %(name)s. "
                        "Reason: %(err)s.") %
                       {'name': name, 'err': ex})
            LOG.error(message)
            raise ex

        size = int(filesystem.size)
        if new_size < size:
            message = (("Failed to extend file system %(name)s because new "
                        "size %(new_size)d is smaller than old size "
                        "%(size)d.") %
                       {'name': name, 'new_size': new_size, 'size': size})
            LOG.error(message)
            raise VNXBackendError(err=message)
        elif new_size == size:
            return

        if not pool_id:
            pool_manager = self.manager.get_object_manager('pool')
            pool = pool_manager.get(pool_name)
            pool_id = pool.id

        request = self._build_task_package(
            self.xml_builder.ExtendFileSystem(
                self.xml_builder.StoragePool(
                    pool=pool_id,
                    size=six.text_type(new_size - size)
                ),
                fileSystem=filesystem.id,
            )
        )

        response = self._send_request(request)

        if constants.STATUS_OK != response['maxSeverity']:
            message = (("Failed to extend file system %(name)s to new size "
                        "%(new_size)d. Reason: %(err)s.") %
                       {'name': name,
                        'new_size': new_size,
                        'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)

        filesystem.update(dict(volumeSize=new_size))

    def create_from_snapshot(self, name, snap_name, source_fs_name, pool_name,
                             mover_name, connect_id):
        create_fs_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_fs',
            '-name', name,
            '-type', 'uxfs',
            '-create',
            'samesize=' + source_fs_name,
            'pool=%s' % pool_name,
            'storage=SINGLE',
            'worm=off',
            '-thin', 'no',
            '-option', 'slice=y',
        ]

        self._execute_cmd(create_fs_cmd)

        ro_mount_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_mount', mover_name,
            '-option', 'ro',
            name,
            '/%s' % name,
        ]
        self._execute_cmd(ro_mount_cmd)

        session_name = name + ':' + snap_name
        copy_ckpt_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_copy',
            '-name', session_name[0:63],
            '-source', '-ckpt', snap_name,
            '-destination', '-fs', name,
            '-interconnect',
            'id=%s' % connect_id,
            '-overwrite_destination',
            '-full_copy',
        ]

        try:
            self._execute_cmd(copy_ckpt_cmd, check_exit_code=True)
        except SSHExecutionError as expt:
            message = (("Failed to copy content from snapshot %(snap)s to "
                        "file system %(filesystem)s. Reason: %(err)s.") %
                       {'snap': snap_name,
                        'filesystem': name,
                        'err': six.text_type(expt)})
            LOG.error(message)

        # When an error happens during nas_copy, we need to continue
        # deleting the checkpoint of the target file system if it exists.
        query_fs_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_fs',
            '-info', name,
        ]
        out, err = self._execute_cmd(query_fs_cmd)
        re_ckpts = r'ckpts\s*=\s*(.*)\s*'
        m = re.search(re_ckpts, out)
        if m is not None:
            ckpts = m.group(1)
            for ckpt in re.split(',', ckpts):
                umount_ckpt_cmd = [
                    'env', 'NAS_DB=/nas',
                    '/nas/bin/server_umount', mover_name,
                    '-perm', ckpt,
                ]
                self._execute_cmd(umount_ckpt_cmd)
                delete_ckpt_cmd = [
                    'env', 'NAS_DB=/nas', '/nas/bin/nas_fs',
                    '-delete', ckpt,
                    '-Force',
                ]
                self._execute_cmd(delete_ckpt_cmd)

        rw_mount_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_mount', mover_name,
            '-option', 'rw',
            name,
            '/%s' % name,
        ]
        self._execute_cmd(rw_mount_cmd)

        filesystem = {
            'name': name,
        }
        self.filesystem_map[name] = self.resource_class(self, filesystem)

        return self.filesystem_map[name]
