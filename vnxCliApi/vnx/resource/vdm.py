# coding=utf-8
from __future__ import unicode_literals

import logging
import re

from retryz import retry

from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXBackendError, \
    ObjectNotFound, VNXInvalidMoverID
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Cedric Zhuang'

LOG = logging.getLogger(__name__)


class VNXVdm(file_resource.Resource):
    def delete(self):
        self.manager.delete(self.name)

    def attach_nfs_interface(self, if_name):
        self.manager.attach_nfs_interface(self.name, if_name)

    def detach_nfs_interface(self, if_name):
        self.manager.detach_nfs_interface(self.name, if_name)

    def get_interfaces(self):
        return self.manager.get_interfaces(self.name)


class VDMManager(file_resource.ResourceManager):
    """Manage :class:`Pool` resources."""
    resource_class = VNXVdm

    def __init__(self, manager):
        super(VDMManager, self).__init__(manager)
        self.vdm_map = dict()

    @retry(on_error=VNXInvalidMoverID)
    def create(self, name, mover_name):
        mover = self._get_mover(mover_name, False)

        request = self._build_task_package(
            self.xml_builder.NewVdm(mover=mover.id, name=name)
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            # Note: Mover ID will be updated, so the next request will not
            # throw the exception VNXInvalidMoverID
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._response_validation(response, constants.MSG_VDM_EXIST):
            LOG.warn("VDM %(name)s already exists. Skip the creation.",
                     {'name': name})
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to create VDM %(name)s on mover "
                       "%(mover_name)s. Reason: %(err)s." %
                       {'name': name,
                        'mover_name': mover_name,
                        'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)

        self.vdm_map[name] = self.resource_class(self, dict(name=name))

        return self.vdm_map[name]

    def get(self, name):
        if self._cache_missed(name, self.vdm_map):
            self.get_all()

            if name not in self.vdm_map:
                message = ("Failed to get VDM %(name)s information." %
                           {'name': name})
                LOG.error(message)
                raise ObjectNotFound(err=message)

        return self.vdm_map[name]

    def get_all(self):
        request = self._build_query_package(
            self.xml_builder.VdmQueryParams()
        )

        response = self._send_request(request)

        if constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to get vdms information. "
                       "Status: %(status)s, Reason: %(err)s." %
                       {'status': response['maxSeverity'],
                        'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)
        elif not response['objects']:
            message = "No VDM is available."
            LOG.error(message)
            raise ObjectNotFound(err=message)

        for item in response['objects']:
            vdm_name = item['name']
            if vdm_name not in self.vdm_map:
                self.vdm_map[vdm_name] = self.resource_class(self, item,
                                                             loaded=True)
            else:
                self.vdm_map[vdm_name].update(item)

        return self.vdm_map

    def delete(self, name):
        try:
            vdm = self.get(name)
        except ObjectNotFound:
            LOG.warn("VDM %s not found. Skip the deletion.", name)
            return
        except VNXBackendError as ex:
            message = ("Failed to get VDM by name %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': ex})
            LOG.error(message)
            raise VNXBackendError(err=message)

        request = self._build_task_package(
            self.xml_builder.DeleteVdm(vdm=vdm.id)
        )

        response = self._send_request(request)

        if constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to delete VDM %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)

        if name in self.vdm_map:
            self.vdm_map.pop(name)

    def attach_nfs_interface(self, vdm_name, if_name):

        command_attach_nfs_interface = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_server',
            '-vdm', vdm_name,
            '-attach', if_name,
        ]

        self._execute_cmd(command_attach_nfs_interface)

    def detach_nfs_interface(self, vdm_name, if_name):

        command_detach_nfs_interface = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_server',
            '-vdm', vdm_name,
            '-detach', if_name,
        ]

        try:
            self._execute_cmd(command_detach_nfs_interface,
                              check_exit_code=True)
        except SSHExecutionError:
            interfaces = self.get_interfaces(vdm_name)
            if if_name not in interfaces['nfs']:
                LOG.debug("Failed to detach interface %(interface)s "
                          "from mover %(mover_name)s.",
                          {'interface': if_name, 'mover_name': vdm_name})
            else:
                message = ("Failed to detach interface %(interface)s "
                           "from mover %(mover_name)s." %
                           {'interface': if_name, 'mover_name': vdm_name})
                LOG.error(message)
                raise VNXBackendError(err=message)

    def get_interfaces(self, vdm_name):
        interfaces = {
            'cifs': [],
            'nfs': [],
        }

        re_pattern = ('Interfaces to services mapping:'
                      '\s*(?P<interfaces>(\s*interface=.*)*)')

        command_get_interfaces = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_server',
            '-i',
            '-vdm', vdm_name,
        ]

        out, err = self._execute_cmd(command_get_interfaces)

        m = re.search(re_pattern, out)
        if m:
            if_list = m.group('interfaces').split('\n')
            for i in if_list:
                m_if = re.search('\s*interface=(?P<if>.*)\s*:'
                                 '\s*(?P<type>.*)\s*', i)
                if m_if:
                    if_name = m_if.group('if').strip()
                    if 'cifs' == m_if.group('type') and if_name != '':
                        interfaces['cifs'].append(if_name)
                    elif 'vdm' == m_if.group('type') and if_name != '':
                        interfaces['nfs'].append(if_name)

        return interfaces
