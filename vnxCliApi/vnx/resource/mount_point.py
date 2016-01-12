# coding=utf-8
from __future__ import unicode_literals

import logging

from retryz import retry

from vnxCliApi.exception import VNXInvalidMoverID, VNXBackendError, \
    ObjectNotFound
from vnxCliApi.lib.common import decorate_all_methods
from vnxCliApi.lib.common import log_enter_exit
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


@decorate_all_methods(log_enter_exit)
class MountPoint(file_resource.Resource):
    def __init__(self, manager, info, loaded=False):
        attribute_map = {
            'filesystem_id': 'fileSystem',
            'mover_id': 'mover',
            'mover_name': 'mover_name',
            'is_vdm': 'moverIdIsVdm',
            'path': 'path',
        }

        super(MountPoint, self).__init__(manager, info, attribute_map, loaded)

    def delete(self):
        self.manager.delete(self.path, self.mover_name, is_vdm=self.is_vdm)


@decorate_all_methods(log_enter_exit)
class MountPointManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = MountPoint

    def __init__(self, manager):
        super(MountPointManager, self).__init__(manager)
        self.mount_map = dict()

    @retry(on_error=VNXInvalidMoverID)
    def create(self, mount_path, fs_name, mover_name, is_vdm=True):
        filesystem_manager = self.manager.get_object_manager('filesystem')
        filesystem = filesystem_manager.get(fs_name)

        mover = self._get_mover(mover_name, is_vdm)

        request = self._build_task_package(
            self.xml_builder.NewMount(
                self.xml_builder.MoverOrVdm(
                    mover=mover.id,
                    moverIdIsVdm='true' if is_vdm else 'false',
                ),
                fileSystem=filesystem.id,
                path=mount_path
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._is_mount_point_already_existent(response):
            log.warn(("Mount Point %(mount)s already exists. "
                      "Skip the creation."), {'mount': mount_path})
        elif constants.STATUS_OK != response['maxSeverity']:
            message = (('Failed to create Mount Point %(mount)s for '
                        'file system %(fs_name)s. Reason: %(err)s.') %
                       {'mount': mount_path,
                        'fs_name': fs_name,
                        'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        mount_point = {
            'path': mount_path,
            'fileSystem': filesystem.id,
            'mover': mover.id,
            'mover_name': mover_name,
            'moverIdIsVdm': is_vdm,
        }

        key = mount_path + '_' + mover.id
        self.mount_map[key] = self.resource_class(self, mount_point)

        return self.mount_map[key]

    def _is_mount_point_already_existent(self, response):
        """Translate different status to ok/error status."""
        msg_codes = self._get_problem_message_codes(response['problems'])
        message = self._get_problem_messages(response['problems'])

        for code, msg in zip(msg_codes, message):
            if (code == constants.MSG_GENERAL_ERROR and
                    'Mount already exists' in msg):
                return True

        return False

    def get_resource(self, resource):
        return self.get(resource.path,
                        mover_name=resource.mover_name,
                        is_vdm=resource.is_vdm)

    @retry(on_error=VNXInvalidMoverID)
    def get(self, path, mover_name=None, is_vdm=True):
        mover = self._get_mover(mover_name, is_vdm)

        key = path + '_' + mover.id
        if self._cache_missed(key, self.mount_map):
            request = self._build_query_package(
                self.xml_builder.MountQueryParams(
                    self.xml_builder.MoverOrVdm(
                        mover=mover.id,
                        moverIdIsVdm='true' if is_vdm else 'false'
                    )
                )
            )

            response = self._send_request(request)

            if self._response_validation(response,
                                         constants.MSG_INVALID_MOVER_ID):
                mover.update()
                raise VNXInvalidMoverID(id=mover.id)
            elif constants.STATUS_OK != response['maxSeverity']:
                message = (("Failed to get mountpoint information. "
                            "Status: %(status)s, Reason: %(err)s.") %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                log.error(message)
                raise VNXBackendError(err=message)

            if not response['objects']:
                message = (("No mountpoint is available. "
                            "Status: %(status)s, Reason: %(err)s.") %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                log.error(message)
                raise ObjectNotFound(err=message)

            for item in response['objects']:
                item['mover_name'] = mover_name
                dict_key = item['path'] + '_' + mover.id
                self.mount_map[dict_key] = self.resource_class(
                    self, item, loaded=True)

        if key not in self.mount_map:
            message = ("Failed to get mountpoint %(path)s information."
                       % {'path': path})
            log.error(message)
            raise ObjectNotFound(err=message)

        return self.mount_map[key]

    @retry(on_error=VNXInvalidMoverID)
    def delete(self, mount_path, mover_name=None, is_vdm=True):
        mover = self._get_mover(mover_name, is_vdm)

        request = self._build_task_package(
            self.xml_builder.DeleteMount(
                mover=mover.id,
                moverIdIsVdm='true' if is_vdm else 'false',
                path=mount_path
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._is_mount_point_nonexistent(response):
            log.warn(('Mount point %(mount)s on mover %(mover_name)s '
                      'not found.'),
                     {'mount': mount_path, 'mover_name': mover_name})

            return
        elif constants.STATUS_OK != response['maxSeverity']:
            message = (('Failed to delete mount point %(mount)s on mover '
                        '%(mover_name)s. Reason: %(err)s.') %
                       {'mount': mount_path,
                        'mover_name': mover_name,
                        'err': response})
            log.error(message)
            raise VNXBackendError(err=message)

        key = mount_path + '_' + mover.id
        if key in self.mount_map:
            self.mount_map.pop(key)

    def _is_mount_point_nonexistent(self, response):
        """Translate different status to ok/error status."""
        msg_codes = self._get_problem_message_codes(response['problems'])
        message = self._get_problem_messages(response['problems'])

        for code, msg in zip(msg_codes, message):
            if ((code == constants.MSG_GENERAL_ERROR and msg.find(
                'No such path or invalid operation') != -1) or
                    code == constants.MSG_INVALID_VDM_ID or
                    code == constants.MSG_INVALID_MOVER_ID):
                return True

        return False
