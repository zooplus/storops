# coding=utf-8
from __future__ import unicode_literals

import logging
from functools import partial

from vnxCliApi.exception import VNXBackendError, ObjectNotFound, \
    VNXInvalidMoverID
from vnxCliApi.lib import converter
from vnxCliApi.lib.common import decorate_all_methods, log_enter_exit, \
    retry_per_30_s
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)

retry = partial(retry_per_30_s, on_error=VNXInvalidMoverID)


@decorate_all_methods(log_enter_exit)
class CIFSServer(file_resource.Resource):
    def __init__(self, manager, info, loaded=False):
        attribute_map = {
            'name': 'name',
            'comp_name': 'compName',
            'aliases': 'Aliases',
            'domain': 'domain',
            'domain_joined': 'domainJoined',
            'interfaces': 'interfaces',
            'mover_name': 'mover_name',
            'mover_id': 'mover',
            'is_vdm': 'moverIdIsVdm',
            'type': 'type',
        }

        super(CIFSServer, self).__init__(manager, info, attribute_map, loaded)

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
        self.manager.modify(cifs_server_args)

    def delete(self):
        self.manager.delete(self.comp_name, self.mover_name, self.is_vdm)


@decorate_all_methods(log_enter_exit)
class CIFSServerManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = CIFSServer

    def __init__(self, manager):
        super(CIFSServerManager, self).__init__(manager)
        self.server_map = dict()

    @retry()
    def create(self, server_args):
        comp_name = server_args['name']
        # Maximum of 14 characters for netBIOS name
        name = server_args['name'][-14:]
        # Maximum of 12 characters for alias name
        alias_name = server_args['name'][-12:]
        interfaces = server_args['interface_ip']
        domain_name = server_args['domain_name']
        user_name = server_args['user_name']
        password = server_args['password']
        mover_name = server_args['mover_name']
        is_vdm = server_args['is_vdm']

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
                compName=comp_name,
                domain=domain_name,
                interfaces=interfaces,
                name=name
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            try:
                cifs_server = self.get(comp_name, mover_name, is_vdm)
                if cifs_server.domain_joined:
                    return self.server_map[comp_name]
            except (ObjectNotFound, VNXBackendError):
                message = ("Failed to create CIFS server %(name)s. "
                           "Reason: %(err)s." %
                           {'name': name,
                            'err': response['problems']})
                log.error(message)
                raise VNXBackendError(err=message)

        cifs_server = {
            'compName': comp_name,
            'name': name,
            'mover_name': mover.name,
            'mover': mover.id,
            'moverIdIsVdm': is_vdm,
        }
        self.server_map[comp_name] = self.resource_class(self, cifs_server)

        return self.server_map[comp_name]

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
    def modify(self, server_args):
        """Make CIFS server join or un-join the domain.

        :param server_args: Dictionary for CIFS server modification
            name: CIFS server name instead of compName
            domain_joined: True for joining the domain, false for un-joining
            username: User name under which the domain is joined
            password: Password associated with the user name
            mover_name: mover or VDM name
            is_vdm: Boolean to indicate mover or VDM
        :raises exception.EMCVnxXMLAPIError: if modification fails.
        """
        name = server_args['name']
        domain_joined = server_args['domain_joined']
        user_name = server_args['username']
        password = server_args['password']
        mover_name = server_args['mover_name']

        if 'is_vdm' in server_args.keys():
            is_vdm = server_args['is_vdm']
        else:
            is_vdm = True

        mover = self._get_mover(mover_name, is_vdm)

        request = self._build_task_package(
            self.xml_builder.ModifyW2KCifsServer(
                self.xml_builder.DomainSetting(
                    joinDomain=converter.boolean_to_str(domain_joined),
                    password=password,
                    userName=user_name,
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
