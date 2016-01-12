# coding=utf-8
from __future__ import unicode_literals

import logging
import re

import vnxCliApi.vnx.constants as const
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.lib.common import decorate_all_methods, log_enter_exit
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

LOG = logging.getLogger(__name__)


@decorate_all_methods(log_enter_exit)
class MoverRef(file_resource.Resource):
    def __init__(self, manager, info, loaded=False):
        attribute_map = {
            'name': 'name',
            'id': 'mover',
        }

        super(MoverRef, self).__init__(manager, info, attribute_map, loaded)


@decorate_all_methods(log_enter_exit)
class MoverRefManager(file_resource.ResourceManager):
    """Manage :class:`Pool` resources."""
    resource_class = MoverRef

    def __init__(self, manager):
        super(MoverRefManager, self).__init__(manager)
        self.mover_ref_map = dict()

    def get(self, name):
        if self._cache_missed(name, self.mover_ref_map):
            request = self._build_query_package(
                self.xml_builder.MoverQueryParams(
                    self.xml_builder.AspectSelection(movers='true')
                )
            )

            response = self._send_request(request)

            if const.STATUS_ERROR == response['maxSeverity']:
                message = (("Failed to get movers information. "
                            "Status: %(status)s. Reason: %(err)s.") %
                           {'status': response['maxSeverity'],
                            'err': response['problems']})
                LOG.error(message)
                raise VNXBackendError(err=message)

            for item in response['objects']:
                mover_name = item['name']
                if mover_name not in self.mover_ref_map:
                    self.mover_ref_map[mover_name] = self.resource_class(
                        self, item, loaded=True)
                else:
                    self.mover_ref_map[mover_name].update(item)

        if (name not in self.mover_ref_map or
                self.mover_ref_map[name].id == ''):
            message = ("Failed to get mover by name %(name)s." %
                       {'name': name})
            LOG.error(message)
            raise ObjectNotFound(err=message)

        return self.mover_ref_map[name]


@decorate_all_methods(log_enter_exit)
class Mover(file_resource.Resource):
    def __init__(self, manager, info, loaded=False):
        attribute_map = {
            'name': 'name',
            'id': 'mover',
            'status': 'maxSeverity',
            'version': 'version',
            'uptime': 'uptime',
            'role': 'role',
            'interfaces': 'MoverInterface',
            'devices': 'LogicalNetworkDevice',
            'dns_domain': 'MoverDnsDomain',
        }

        super(Mover, self).__init__(manager, info, attribute_map, loaded)

    def get_interconnect_id(self, dest_mover=None):
        if dest_mover:
            return self.manager.get_interconnect_id(self.name,
                                                    dest_mover.name)
        else:
            return self.manager.get_interconnect_id(self.name, self.name)

    def get_physical_devices(self):
        return self.manager.get_physical_devices(self.name)


@decorate_all_methods(log_enter_exit)
class MoverManager(file_resource.ResourceManager):
    """Manage :class:`Pool` resources."""
    resource_class = Mover

    def __init__(self, manager):
        super(MoverManager, self).__init__(manager)
        self.mover_map = dict()

    def get(self, name):
        mover_ref_manager = self.manager.get_object_manager('mover_ref')

        if self._cache_missed(name, self.mover_map):
            mover_ref = mover_ref_manager.get(name)

            request = self._build_query_package(
                self.xml_builder.MoverQueryParams(
                    self.xml_builder.AspectSelection(
                        moverDeduplicationSettings='true',
                        moverDnsDomains='true',
                        moverInterfaces='true',
                        moverNetworkDevices='true',
                        moverNisDomains='true',
                        moverRoutes='true',
                        movers='true',
                        moverStatuses='true'
                    ),
                    mover=mover_ref.id
                )
            )

            response = self._send_request(request)

            message = ("Failed to get mover by name %(name)s." %
                       {'name': name})
            if const.STATUS_ERROR == response['maxSeverity']:
                LOG.error(message)
                raise VNXBackendError(err=message)
            elif not response['objects']:
                LOG.error(message)
                raise ObjectNotFound(err=message)

            item = response['objects'][0]
            if name not in self.mover_map:
                self.mover_map[name] = self.resource_class(self, item,
                                                           loaded=True)
            else:
                self.mover_map[name].update(item)

            mover = self.mover_map[name]

            internal_devices = []
            if mover.interfaces:
                for interface in mover.interfaces:
                    if self._is_internal_device(interface['device']):
                        internal_devices.append(interface)

                mover.interfaces = [var for var in mover.interfaces if
                                    var not in internal_devices]

        return self.mover_map[name]

    @staticmethod
    def _is_internal_device(device):
        for device_type in ('mge', 'fxg', 'tks', 'fsn'):
            if device.find(device_type) == 0:
                return True
        return False

    def get_interconnect_id(self, source, destination):
        header = [
            'id',
            'name',
            'source_server',
            'destination_system',
            'destination_server',
        ]

        conn_id = None

        command_nas_cel = [
            'env', 'NAS_DB=/nas', '/nas/bin/nas_cel',
            '-interconnect', '-l',
        ]
        out, err = self._execute_cmd(command_nas_cel)

        lines = out.strip().split('\n')
        for line in lines:
            if line.strip().split() == header:
                LOG.info('Found the header of the command '
                         '/nas/bin/nas_cel -interconnect -l.')
            else:
                interconn = line.strip().split()
                if interconn[2] == source and interconn[4] == destination:
                    conn_id = interconn[0]

        return conn_id

    def get_physical_devices(self, mover_name):

        physical_network_devices = []

        cmd_sysconfig = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_sysconfig', mover_name,
            '-pci'
        ]

        out, err = self._execute_cmd(cmd_sysconfig)

        re_pattern = ('0:\s*(?P<name>\S+)\s*IRQ:\s*(?P<irq>\d+)\n'
                      '.*\n'
                      '\s*Link:\s*(?P<link>[A-Za-z]+)')

        for device in re.finditer(re_pattern, out):
            if 'Up' in device.group('link'):
                physical_network_devices.append(device.group('name'))

        return physical_network_devices
