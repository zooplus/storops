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

import six

from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


class VNXFsSnap(file_resource.Resource):
    def delete(self):
        self.manager.delete(self.name)


class SnapshotManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = VNXFsSnap

    def __init__(self, manager):
        super(SnapshotManager, self).__init__(manager)
        self.snapshot_map = dict()

    def create(self, name, fs_name, pool_id, ckpt_size=None):
        filesystem_manager = self.manager.get_object_manager('filesystem')
        filesystem = filesystem_manager.get(fs_name)

        if ckpt_size:
            elt_pool = self.xml_builder.StoragePool(
                pool=pool_id,
                size=six.text_type(ckpt_size)
            )
        else:
            elt_pool = self.xml_builder.StoragePool(pool=pool_id)

        new_ckpt = self.xml_builder.NewCheckpoint(
            self.xml_builder.SpaceAllocationMethod(
                elt_pool
            ),
            checkpointOf=filesystem.id,
            name=name
        )

        request = self._build_task_package(new_ckpt)

        response = self._send_request(request)

        if self._response_validation(response, constants.MSG_SNAP_EXIST):
            log.warn("Snapshot %(name)s already exists. "
                     "Skip the creation.",
                     {'name': name})
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to create snapshot %(name)s on "
                       "filesystem %(fs_name)s. Reason: %(err)s." %
                       {'name': name,
                        'fs_name': fs_name,
                        'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        snapshot = {
            'name': name,
        }
        self.snapshot_map[name] = self.resource_class(self, snapshot)

        return self.snapshot_map[name]

    def get(self, name):
        if self._cache_missed(name, self.snapshot_map):
            request = self._build_query_package(
                self.xml_builder.CheckpointQueryParams(
                    self.xml_builder.Alias(name=name)
                )
            )

            response = self._send_request(request)

            if constants.STATUS_OK != response['maxSeverity']:
                message = ("Failed to get snapshot information. "
                           "Status: %(status)s, Reason: %(err)s." %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                log.error(message)
                raise VNXBackendError(err=message)

            if not response['objects']:
                message = ("Snapshot is not available. "
                           "Status: %(status)s, Reason: %(err)s." %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                log.error(message)
                raise ObjectNotFound(err=message)

            snapshot = response['objects'][0]
            if name not in self.snapshot_map:
                self.snapshot_map[name] = self.resource_class(
                    self, snapshot, loaded=True)
            else:
                self.snapshot_map[name].update(snapshot)

        return self.snapshot_map[name]

    def delete(self, name):
        try:
            snapshot = self.get(name)
        except ObjectNotFound:
            log.warn("Snapshot %s not found. Skip the deletion.",
                     name)
            return
        except VNXBackendError as ex:
            message = ("Failed to get snapshot by name %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': ex})
            log.error(message)
            raise ex

        request = self._build_task_package(
            self.xml_builder.DeleteCheckpoint(checkpoint=snapshot.id)
        )

        response = self._send_request(request)
        if constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to delete snapshot %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        if name in self.snapshot_map:
            self.snapshot_map.pop(name)
