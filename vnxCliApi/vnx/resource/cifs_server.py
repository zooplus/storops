# coding=utf-8
from __future__ import unicode_literals

import logging
from functools import partial

from vnxCliApi.exception import VNXBackendError, ObjectNotFound, \
    VNXInvalidMoverID
from vnxCliApi.lib import converter
from vnxCliApi.lib.common import retry_per_30_s
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)

retry = partial(retry_per_30_s, on_error=VNXInvalidMoverID)


class VNXCifsServer(file_resource.Resource):
    def modify(self, username, password):
        # Join/unjoin CIFS server into/from the domain
        cifs_server_args = {
            'name': self.name,
            'domain_joined': not self.domain_joined,
            'username': username,
            'password': password,
            'mover_name': self.mover_name,
            'is_vdm': self.is_vdm,
        }
        self.manager.modify(**cifs_server_args)

    def delete(self):
        self.manager.delete(self.comp_name, self.mover_name, self.is_vdm)


class CIFSServerManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = VNXCifsServer

    def __init__(self, manager):
        super(CIFSServerManager, self).__init__(manager)
        self.server_map = dict()

    @retry()
    def create(self, name, interface_ip, mover_name,
               is_vdm=True, net_bios_name=None, alias_name=None,
               domain_name=None, user_name=None, password=None):
        # Maximum of 14 characters for netBIOS name
        if net_bios_name is None:
            net_bios_name = name[-14:]
        # Maximum of 12 characters for alias name
        if alias_name is None:
            alias_name = name[-12:]

        mover = self._get_mover(mover_name, is_vdm)

        alias_name_list = [self.xml_builder.li(alias_name)]

        request = self._build_task_package(
            self.xml_builder.NewW2KCifsServer(
                self.xml_builder.MoverOrVdm(
                    mover=mover.id,
                    moverIdIsVdm=converter.boolean_to_str(is_vdm)
                ),
                self.xml_builder.Aliases(*alias_name_list),
                self.xml_builder.JoinDomain(userName=user_name,
                                            password=password),
                compName=name,
                domain=domain_name,
                interfaces=interface_ip,
                name=net_bios_name
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            try:
                cifs_server = self.get(name, mover_name, is_vdm)
                if cifs_server.domain_joined:
                    return self.server_map[name]
            except (ObjectNotFound, VNXBackendError):
                message = ("Failed to create CIFS server %(name)s. "
                           "Reason: %(err)s." %
                           {'name': net_bios_name,
                            'err': response['problems']})
                log.error(message)
                raise VNXBackendError(err=message)

        cifs_server = {
            'compName': name,
            'name': net_bios_name,
            'mover_name': mover.name,
            'mover': mover.id,
            'moverIdIsVdm': is_vdm,
        }
        self.server_map[name] = self.resource_class(self, cifs_server)

        return self.server_map[name]

    def get_resource(self, resource):
        return self.get(
            resource.comp_name, resource.mover_name, resource.is_vdm)

    def get(self, comp_name, mover_name, is_vdm=True):
        # name is compName
        name = comp_name.lower()

        if not self._cache_missed(name, self.server_map):
            return self.server_map[name]

        self.get_all(mover_name, is_vdm)

        cifs = self.server_map.get(name)
        if cifs and mover_name == cifs.mover_name and is_vdm == cifs.is_vdm:
            return cifs

        message = ("Failed to get CIFS server %(name)s information on "
                   "mover %(mover_name)s." %
                   {'name': name, 'mover_name': mover_name})
        log.error(message)
        raise ObjectNotFound(err=message)

    @retry()
    def get_all(self, mover_name, is_vdm=True):
        mover = self._get_mover(mover_name, is_vdm)

        request = self._build_query_package(
            self.xml_builder.CifsServerQueryParams(
                self.xml_builder.MoverOrVdm(
                    mover=mover.id,
                    moverIdIsVdm=converter.boolean_to_str(is_vdm)
                )
            )
        )

        response = self._send_request(request)
        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to get CIFS server information. "
                       "Status: %(status)s, Reason: %(err)s." %
                       {'status': response['maxSeverity'],
                        'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        for item in response['objects']:
            # Add the additional mover information into resource
            item['mover_name'] = mover.name
            item['mover_id'] = mover.id

            item['moverIdIsVdm'] = converter.to_bool(
                item['moverIdIsVdm'])
            item['domainJoined'] = converter.to_bool(
                item['domainJoined'])

            comp_name = item['compName'].lower()
            if comp_name not in self.server_map:
                self.server_map[comp_name] = self.resource_class(
                    self, item, loaded=True)
            else:
                self.server_map[comp_name].update(item)

        return self.server_map

    @retry()
    def modify(self, name, mover_name, is_vdm=True,
               domain_joined=None, username=None, password=None):
        """Make CIFS server join or un-join the domain.

        :param name: CIFS server name instead of compName
        :param domain_joined: True for joining the domain, false for un-joining
        :param username: User name under which the domain is joined
        :param password: Password associated with the user name
        :param mover_name: mover or VDM name
        :param is_vdm: Boolean to indicate mover or VDM
        :raises exception.EMCVnxXMLAPIError: if modification fails.
        """

        mover = self._get_mover(mover_name, is_vdm)

        request = self._build_task_package(
            self.xml_builder.ModifyW2KCifsServer(
                self.xml_builder.DomainSetting(
                    joinDomain=converter.boolean_to_str(domain_joined),
                    password=password,
                    userName=username,
                ),
                mover=mover.id,
                moverIdIsVdm=converter.boolean_to_str(is_vdm),
                name=name
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._ignore_modification_error(response, domain_joined):
            return
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to modify CIFS server %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name,
                        'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

    def _ignore_modification_error(self, response, domain_joined):
        if self._response_validation(response, constants.MSG_JOIN_DOMAIN):
            return domain_joined
        elif self._response_validation(response, constants.MSG_UNJOIN_DOMAIN):
            return not domain_joined

        return False

    def delete(self, comp_name, mover_name, is_vdm=True):
        try:
            cifs_server = self.get(comp_name, mover_name, is_vdm)
        except ObjectNotFound:
            log.warn("CIFS server %(name)s on mover %(mover_name)s "
                     "not found. Skip the deletion.",
                     {'name': comp_name, 'mover_name': mover_name})
            return
        except VNXBackendError as ex:
            message = ("Failed to delete CIFS server %(name)s. "
                       "Reason: %(err)s." %
                       {'name': comp_name, 'err': ex})
            log.error(message)
            raise VNXBackendError(err=message)

        server_name = cifs_server.name

        mover = self._get_mover(mover_name, is_vdm)

        request = self._build_task_package(
            self.xml_builder.DeleteCifsServer(
                mover=mover.id,
                moverIdIsVdm=converter.boolean_to_str(is_vdm),
                name=server_name
            )
        )

        response = self._send_request(request)

        if constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to delete CIFS server %(name)s. "
                       "Reason: %(err)s." %
                       {'name': comp_name, 'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        if comp_name in self.server_map:
            self.server_map.pop(comp_name)
