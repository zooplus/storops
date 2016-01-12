# coding=utf-8
from __future__ import unicode_literals

import logging

import six
from retryz import retry

from vnxCliApi.exception import VNXInvalidMoverID, VNXBackendError, \
    ObjectNotFound
from vnxCliApi.lib.common import decorate_all_methods, log_enter_exit
from vnxCliApi.vnx import constants as const
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


@decorate_all_methods(log_enter_exit)
class MoverInterface(file_resource.Resource):
    def __init__(self, manager, info, loaded=False):
        attribute_map = {
            'name': 'name',
            'mover_name': 'mover_name',
            'device': 'device',
            'ip_addr': 'ipAddress',
            'ip_version': 'ipVersion',
            'net_mask': 'netMask',
            'up': 'up',
            'vlan_id': 'vlanid',
        }

        super(MoverInterface, self).__init__(
            manager, info, attribute_map, loaded)

    def delete(self):
        self.manager.delete(self.ip_addr, self.mover_name)


@decorate_all_methods(log_enter_exit)
class MoverInterfaceManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = MoverInterface

    # Maximum of 32 characters for mover interface name
    max_len_of_interface_name = 32

    def __init__(self, manager):
        super(MoverInterfaceManager, self).__init__(manager)

    @retry(on_error=VNXInvalidMoverID)
    def create(self, interface):

        name = interface['name']
        if len(name) > MoverInterfaceManager.max_len_of_interface_name:
            name = name[:MoverInterfaceManager.max_len_of_interface_name]

        device_name = interface['device_name']
        ip_addr = interface['ip']
        mover_name = interface['mover_name']
        net_mask = interface['net_mask']
        vlan_id = interface['vlan_id'] if interface['vlan_id'] else -1

        mover = self._get_mover(mover_name, False)

        request = self._build_task_package(
            self.xml_builder.NewMoverInterface(
                device=device_name,
                ipAddress=six.text_type(ip_addr),
                mover=mover.id,
                name=name,
                netMask=net_mask,
                vlanid=six.text_type(vlan_id)
            )
        )

        response = self._send_request(request)

        if (self._response_validation(response,
                                      const.MSG_INVALID_MOVER_ID)):
            # Note: Mover ID will be updated, so the next request will not
            # throw the exception VNXInvalidMoverID
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._response_validation(response,
                                       const.MSG_INTERFACE_NAME_EXIST):
            LOG.warn(("Mover interface name %s already exists. "
                      "Skip the creation."), name)
        elif self._response_validation(response,
                                       const.MSG_INTERFACE_EXIST):
            LOG.warn(("Mover interface IP %s already exists. "
                      "Skip the creation."), ip_addr)
        elif self._response_validation(response,
                                       const.MSG_INTERFACE_INVALID_VLAN_ID):
            # When fail to create a mover interface with the specified
            # vlan id, VNX will leave a interface with vlan id 0 in the
            # backend. So we should explicitly remove the interface.
            try:
                self.delete(six.text_type(ip_addr), mover_name)
            except VNXBackendError:
                pass

            message = (("Invalid vlan id %s. Other interfaces on this "
                        "subnet are in a different vlan.") % vlan_id)
            LOG.error(message)
            raise VNXBackendError(err=message)
        elif const.STATUS_OK != response['maxSeverity']:
            message = (("Failed to create mover interface %(interface)s. "
                        "Reason: %(err)s.") %
                       {'interface': interface,
                        'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)

        interface = {
            'name': name,
            'ipAddress': six.text_type(ip_addr),
            'mover_name': mover_name,
            'vlanid': six.text_type(interface['vlan_id']),
            'netMask': interface['net_mask'],
            'device': interface['device_name'],
        }
        return self.resource_class(self, interface)

    def get_resource(self, resource):
        return self.get(resource.name, resource.mover_name)

    def get(self, name, mover_name):
        if len(name) > MoverInterfaceManager.max_len_of_interface_name:
            name = name[:MoverInterfaceManager.max_len_of_interface_name]

        mover_manager = self.manager.get_object_manager('mover')
        try:
            # Poll mover information
            if mover_name in mover_manager.mover_map:
                mover_manager.mover_map[mover_name].set_loaded(False)
            mover = mover_manager.get(mover_name)
            for interface in mover.interfaces:
                if name == interface['name']:
                    interface['mover_name'] = mover_name
                    return self.resource_class(self, interface, loaded=True)
        except (ObjectNotFound, VNXBackendError):
            message = (("Failed to get mover interface %(name)s on "
                        "mover %(mover_name)s.") %
                       {'name': name, 'mover_name': mover_name})
            LOG.error(message)
            raise ObjectNotFound(err=message)

    @retry(on_error=VNXInvalidMoverID)
    def delete(self, ip_addr, mover_name):
        mover = self._get_mover(mover_name, False)

        request = self._build_task_package(
            self.xml_builder.DeleteMoverInterface(
                ipAddress=six.text_type(ip_addr),
                mover=mover.id
            )
        )

        response = self._send_request(request)

        if self._response_validation(response,
                                     const.MSG_INVALID_MOVER_ID):
            # Note: Mover ID will be updated, so the next request will not
            # throw the exception VNXInvalidMoverID
            mover.update()
            raise VNXInvalidMoverID(id=mover.id)
        elif self._response_validation(response,
                                       const.MSG_INTERFACE_NON_EXISTENT):
            LOG.warn("Mover interface %s not found. Skip the deletion.",
                     ip_addr)
            return
        elif const.STATUS_OK != response['maxSeverity']:
            message = (("Failed to delete mover interface %(ip)s on mover "
                        "%(mover)s. Reason: %(err)s.") %
                       {'ip': ip_addr,
                        'mover': mover_name,
                        'err': response['problems']})
            LOG.error(message)
            raise VNXBackendError(err=message)
