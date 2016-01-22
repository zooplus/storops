# coding=utf-8
from __future__ import unicode_literals

import unittest

import mock

from test.vnx.resource.fakes import mock_ssh_connector
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import mover

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import ObjectNotFound, VNXBackendError
from vnxCliApi.vnx.resource import manager

__author__ = 'Jay Xu'


class MoverRefTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()
        self.ssh_hook = utils.SSHSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.VNXFileClient(host, username, password)
        self.mover_ref_manager = mover.MoverRefManager(storage_manager)

        self.mover = fakes.MoverTestData()

    def test_get(self):
        self.hook.append(self.mover.resp_get_ref_succeed())

        xml_connector = self.mover_ref_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        mover_ref = self.mover_ref_manager.get(self.mover.mover_name)
        self.assertIn(self.mover.mover_name,
                      self.mover_ref_manager.mover_ref_map)

        property_map = [
            'name',
            'id',
        ]
        for prop in property_map:
            self.assertIn(prop, mover_ref.__dict__)

        expected_calls = [mock.call(self.mover.req_get_ref())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_but_not_found(self):
        self.hook.append(self.mover.resp_get_ref_succeed(name='other'))

        xml_connector = self.mover_ref_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.mover_ref_manager.get,
                          self.mover.mover_name)

        expected_calls = [mock.call(self.mover.req_get_ref())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_with_error(self):
        self.hook.append(self.mover.resp_get_error())

        xml_connector = self.mover_ref_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mover_ref_manager.get,
                          self.mover.mover_name)

        expected_calls = [mock.call(self.mover.req_get_ref())]
        xml_connector.post.assert_has_calls(expected_calls)


class MoverTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()
        self.ssh_hook = utils.SSHSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.VNXFileClient(host, username, password)
        self.mover_manager = mover.MoverManager(storage_manager)

        self.mover = fakes.MoverTestData()

    def test_get(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_get_succeed())

        xml_connector = self.mover_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        mover = self.mover_manager.get(self.mover.mover_name)

        self.assertIn(self.mover.mover_name, self.mover_manager.mover_map)
        property_map = [
            'name',
            'id',
            'status',
            'version',
            'uptime',
            'role',
            'interfaces',
            'devices',
            'dns_domain',
        ]
        for prop in property_map:
            self.assertIn(prop, mover.__dict__)

        # Invoke get() in the second time to ensure the information from cache
        self.mover_manager.get(self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mover_failed_to_get_mover_ref(self):
        self.hook.append(self.mover.resp_get_error())

        xml_connector = self.mover_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mover_manager.get,
                          self.mover.mover_name)

        expected_calls = [mock.call(self.mover.req_get_ref())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mover_but_not_found(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_get_without_value())

        xml_connector = self.mover_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.mover_manager.get,
                          name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mover_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_get_error())

        xml_connector = self.mover_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mover_manager.get,
                          name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_interconnect_id(self):
        self.ssh_hook.append(self.mover.output_get_interconnect_id())

        ssh_connector = self.mover_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        conn_id = self.mover_manager.get_interconnect_id(
            self.mover.mover_name, self.mover.mover_name)
        self.assertEqual(self.mover.interconnect_id, conn_id)

        ssh_calls = [mock.call(self.mover.cmd_get_interconnect_id(),
                               check_exit_code=False)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_get_physical_devices(self):
        self.ssh_hook.append(self.mover.output_get_physical_devices())

        ssh_connector = self.mover_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        devices = self.mover_manager.get_physical_devices(
            self.mover.mover_name)
        self.assertIn(self.mover.device_name, devices)

        ssh_calls = [mock.call(self.mover.cmd_get_physical_devices(),
                               check_exit_code=False)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_operations_with_mover_resource(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_get_succeed())

        xml_connector = self.mover_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.ssh_hook.append(self.mover.output_get_interconnect_id())
        self.ssh_hook.append(self.mover.output_get_interconnect_id())
        self.ssh_hook.append(self.mover.output_get_physical_devices())

        ssh_connector = self.mover_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        mover = self.mover_manager.get(self.mover.mover_name)

        self.assertIn(self.mover.mover_name, self.mover_manager.mover_map)
        property_map = [
            'name',
            'id',
            'status',
            'version',
            'uptime',
            'role',
            'interfaces',
            'devices',
            'dns_domain',
        ]
        for prop in property_map:
            self.assertIn(prop, mover.__dict__)

        conn_id = mover.get_interconnect_id(mover)
        self.assertEqual(self.mover.interconnect_id, conn_id)

        conn_id = mover.get_interconnect_id()
        self.assertEqual(self.mover.interconnect_id, conn_id)

        devices = mover.get_physical_devices()
        self.assertIn(self.mover.device_name, devices)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        ssh_calls = [
            mock.call(self.mover.cmd_get_interconnect_id(),
                      check_exit_code=False),
            mock.call(self.mover.cmd_get_interconnect_id(),
                      check_exit_code=False),
            mock.call(self.mover.cmd_get_physical_devices(),
                      check_exit_code=False)]
        ssh_connector.execute.assert_has_calls(ssh_calls)
