# coding=utf-8
from __future__ import unicode_literals

import logging

from retryz import retry

from vnxCliApi.exception import VNXInvalidMoverID, VNXBackendError
from vnxCliApi.lib.common import log_enter_exit, decorate_all_methods
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


@decorate_all_methods(log_enter_exit)
class DNSDomain(file_resource.Resource):
    def __init__(self, manager, info, loaded=False):
        attribute_map = {
            'name': 'name',
            'mover_name': 'mover_name',
            'servers': 'servers',
        }

        super(DNSDomain, self).__init__(manager, info, attribute_map, loaded)

    def delete(self):
        self.manager.delete(self.name, self.mover_name)


@decorate_all_methods(log_enter_exit)
class DNSDomainManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = DNSDomain

    def __init__(self, manager):
        super(DNSDomainManager, self).__init__(manager)

    @retry(on_error=VNXInvalidMoverID)
    def create(self, mover_name, name, servers, protocol='udp'):
        mover = self._get_mover(mover_name, False)

        request = self._build_task_package(
            self.xml_builder.NewMoverDnsDomain(
                mover=mover.id,
                name=name,
                servers=servers,
                protocol=protocol
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to create DNS domain %(name)s. "
                       "Reason: %(err)s." %
                       {'name': name, 'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        dns_domain = {
            'name': name,
            'mover_name': mover_name,
            'servers': servers
        }
        return self.resource_class(self, dns_domain)

    @retry(on_error=VNXInvalidMoverID)
    def delete(self, name, mover_name):
        mover = self._get_mover(mover_name, False)

        request = self._build_task_package(
            self.xml_builder.DeleteMoverDnsDomain(
                mover=mover.id,
                name=name
            )
        )

        response = self._send_request(request)
        if self._response_validation(response,
                                     constants.MSG_INVALID_MOVER_ID):
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif constants.STATUS_OK != response['maxSeverity']:
            log.warn("Failed to delete DNS domain %(name)s. "
                     "Reason: %(err)s.",
                     {'name': name, 'err': response['problems']})
