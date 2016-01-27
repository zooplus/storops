# coding=utf-8
from __future__ import unicode_literals

import unittest

import ddt
import mock

from test.vnx.resource.fakes import mock_ssh_connector
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import nas_pool

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import ObjectNotFound, VNXBackendError
from vnxCliApi.vnx.resource import nas_client

__author__ = 'Jay Xu'


@ddt.ddt
class StoragePoolTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = nas_client.VNXNasClient(host, username, password)
        self.pool_manager = nas_pool.PoolManager(storage_manager)

        self.pool = fakes.PoolTestData()

    def test_get_pool(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.pool.resp_get_succeed(id='new_id'))

        xml_connector = self.pool_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        pool = self.pool_manager.get(self.pool.pool_name)
        self.assertIn(self.pool.pool_name, self.pool_manager.pool_map)
        property_map = [
            'name',
            'movers_id',
            'total_size',
            'used_size',
            'disk_type',
            'policies',
            'id',
        ]
        for prop in property_map:
            self.assertIn(prop, pool.__dict__)

        self.pool_manager.get_all()
        update_pool = self.pool_manager.pool_map[self.pool.pool_name]
        self.assertEqual('new_id', update_pool.id)

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.pool.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @ddt.data(fakes.PoolTestData().resp_get_without_value(),
              fakes.PoolTestData().resp_get_succeed(name='other'))
    def test_get_pool_but_not_found(self, xml_resp):
        self.hook.append(xml_resp)

        xml_connector = self.pool_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.pool_manager.get,
                          self.pool.pool_name)

        expected_calls = [mock.call(self.pool.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_pool_with_error(self):
        self.hook.append(self.pool.resp_get_error())

        xml_connector = self.pool_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.pool_manager.get,
                          self.pool.pool_name)

        expected_calls = [mock.call(self.pool.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)
