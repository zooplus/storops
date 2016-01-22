# coding=utf-8
from __future__ import unicode_literals

import logging

from vnxCliApi.exception import ObjectNotFound, VNXBackendError
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class VNXNasPool(file_resource.Resource):
    pass


class PoolManager(file_resource.ResourceManager):
    """Manage :class:`Pool` resources."""
    resource_class = VNXNasPool

    def __init__(self, manager):
        super(PoolManager, self).__init__(manager)
        self.pool_map = dict()

    def get(self, name):
        if self._cache_missed(name, self.pool_map):
            self.get_all()

        if name not in self.pool_map:
            message = ("Failed to get pool %(name)s information." %
                       {'name': name})
            log.error(message)
            raise ObjectNotFound(err=message)

        return self.pool_map[name]

    def get_all(self):
        request = self._build_query_package(
            self.xml_builder.StoragePoolQueryParams()
        )

        response = self._send_request(request)

        if constants.STATUS_OK != response['maxSeverity']:
            message = ("Failed to get pools information. "
                       "Status: %(status)s, Reason: %(err)s." %
                       {'status': response['maxSeverity'],
                        'err': response['problems']})
            log.error(message)
            raise VNXBackendError(err=message)

        if not response['objects']:
            message = "No pool is available."
            log.error(message)
            raise ObjectNotFound(err=message)

        for item in response['objects']:
            name = item['name']
            if name not in self.pool_map:
                self.pool_map[name] = self.resource_class(self, item,
                                                          loaded=True)
            else:
                self.pool_map[name].update(item)

        return self.pool_map
