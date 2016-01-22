# coding=utf-8
from __future__ import unicode_literals

import logging
import re

from retryz import retry

from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXBackendError, \
    VNXInvalidMoverID, ObjectNotFound
from vnxCliApi.lib import converter
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


class VNXCifsShare(file_resource.Resource):
    def delete(self):
        self.manager.delete(self.name, self.mover_name, self.is_vdm)

    def disable_share_access(self):
        self.manager.disable_share_access(self.name, self.mover_name)

    def allow_share_access(self, user_name, domain,
                           access=constants.CIFS_ACL_FULLCONTROL):
        self.manager.allow_share_access(
            self.mover_name, self.name, user_name, domain, access)

    def deny_share_access(self, user_name, domain,
                          access=constants.CIFS_ACL_FULLCONTROL):
        self.manager.deny_share_access(
            self.mover_name, self.name, user_name, domain, access)


class CIFSShareManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = VNXCifsShare

    def __init__(self, manager):
        super(CIFSShareManager, self).__init__(manager)
        self.share_map = dict()

    @retry(on_error=VNXInvalidMoverID)
    def create(self, name, server_name, mover_name, is_vdm=True):
        mover = self._get_mover(mover_name, is_vdm)

        share_path = '/' + name

        request = self._build_task_package(
            self.xml_builder.NewCifsShare(
                self.xml_builder.MoverOrVdm(
                    mover=mover.id,
                    moverIdIsVdm=converter.boolean_to_str(is_vdm)
                ),
                self.xml_builder.CifsServers(self.xml_builder.li(server_name)),
                name=name,
                path=share_path
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to create file share %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        share = {
            'name': name,
            'mover_name': mover_name,
        }
        self.share_map[name] = self.resource_class(self, share)

        return self.share_map[name]

    def get(self, name):
        if self._cache_missed(name, self.share_map):
            request = self._build_query_package(
                self.xml_builder.CifsShareQueryParams(name=name)
            )

            response = self._send_request(request)

            if constants.STATUS_OK != response['maxSeverity']:
                message = ("Failed to get CIFS share information. "
                           "Status: %(status)s, Reason: %(err)s." %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                log.error(message)
                raise VNXBackendError(err=message)

            if not response['objects']:
                message = ("CIFS share %(name)s is not available. "
                           "Status: %(status)s, Reason: %(err)s." %
                           {'name': name,
                            'status': response['maxSeverity'],
                            'err': response['problems']})
                log.error(message)
                raise ObjectNotFound(err=message)

            share = response['objects'][0]
            if name not in self.share_map:
                self.share_map[name] = self.resource_class(
                    self, share, loaded=True)
            else:
                self.share_map[name].update(share)

        return self.share_map[name]

    @retry(on_error=VNXInvalidMoverID)
    def delete(self, name, mover_name, is_vdm=True):
        try:
            share = self.get(name)
        except ObjectNotFound:
            log.warn("CIFS share %s not found. Skip the deletion.",
                     name)
            return
        except VNXBackendError as ex:
            message = ("Failed to get CIFS share by name %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': ex})
            log.error(message)
            raise ex

        mover = self._get_mover(mover_name, is_vdm)

        netbios_names = share.cifs_servers

        request = self._build_task_package(
            self.xml_builder.DeleteCifsShare(
                self.xml_builder.CifsServers(
                    *map(lambda a: self.xml_builder.li(a), netbios_names)),
                mover=mover.id,
                moverIdIsVdm='true' if is_vdm else 'false',
                name=name
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to delete file system %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        if name in self.share_map:
            self.share_map.pop(name)

    def disable_share_access(self, share_name, mover_name):
        cmd_str = 'sharesd %s set noaccess' % share_name
        disable_access = [
            'env', 'NAS_DB=/nas', '/nas/bin/.server_config', mover_name,
            '-v', "%s" % cmd_str,
        ]

        try:
            self._execute_cmd(disable_access, check_exit_code=True)
        except SSHExecutionError as expt:
            message = ('Failed to disable the access to CIFS share '
                       '%(name)s. Reason: %(err)s.' %
                       {'name': share_name, 'err': expt})
            log.error(message)
            raise VNXBackendError(err=message)

    def allow_share_access(self, mover_name, share_name, user_name, domain,
                           access=constants.CIFS_ACL_FULLCONTROL):
        account = user_name + "@" + domain
        allow_str = ('sharesd %(share_name)s grant %(account)s=%(access)s'
                     % {'share_name': share_name,
                        'account': account,
                        'access': access})

        allow_access = [
            'env', 'NAS_DB=/nas', '/nas/bin/.server_config', mover_name,
            '-v', "%s" % allow_str,
        ]

        try:
            self._execute_cmd(allow_access, check_exit_code=True)
        except SSHExecutionError as expt:
            dup_msg = re.compile(r'ACE for %(domain)s\\%(user)s unchanged' %
                                 {'domain': domain, 'user': user_name}, re.I)
            if re.search(dup_msg, expt.stdout):
                log.warn("Duplicate access control entry, "
                         "skipping allow...")
            else:
                message = ('Failed to allow the access %(access)s to '
                           'CIFS share %(name)s. Reason: %(err)s.' %
                           {'access': access, 'name': share_name, 'err': expt})
                log.error(message)
                raise VNXBackendError(err=message)

    def deny_share_access(self, mover_name, share_name, user_name, domain,
                          access=constants.CIFS_ACL_FULLCONTROL):
        account = user_name + "@" + domain
        revoke_str = ('sharesd %(share_name)s revoke %(account)s=%(access)s'
                      % {'share_name': share_name,
                         'account': account,
                         'access': access})

        allow_access = [
            'env', 'NAS_DB=/nas', '/nas/bin/.server_config', mover_name,
            '-v', "%s" % revoke_str,
        ]
        try:
            self._execute_cmd(allow_access, check_exit_code=True)
        except SSHExecutionError as expt:
            not_found_msg = re.compile(
                r'No ACE found for %(domain)s\\%(user)s'
                % {'domain': domain, 'user': user_name}, re.I)
            user_err_msg = re.compile(
                r'Cannot get mapping for %(domain)s\\%(user)s'
                % {'domain': domain, 'user': user_name}, re.I)

            if re.search(not_found_msg, expt.stdout):
                log.warn("No access control entry found, "
                         "skipping deny...")
            elif re.search(user_err_msg, expt.stdout):
                log.warn("User not found on domain, skipping deny...")
            else:
                message = ('Failed to deny the access %(access)s to '
                           'CIFS share %(name)s. Reason: %(err)s.' %
                           {'access': access, 'name': share_name, 'err': expt})
                log.error(message)
                raise VNXBackendError(err=message)
