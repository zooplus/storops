# coding=utf-8
from __future__ import unicode_literals

import unittest

import ddt
import mock
import six

from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import manager

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx.resource import mover_interface

__author__ = 'Jay Xu'


@ddt.ddt
class MoverInterfaceTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.StorageManager(host, username, password)
        self.mover_interface_manager = mover_interface.MoverInterfaceManager(
            storage_manager)

        self.mover = fakes.MoverTestData()

    @ddt.data(fakes.MoverTestData().interface_name1,
              fakes.MoverTestData().long_interface_name)
    def test_create_mover_interface(self, interface_name):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': interface_name,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        mi = self.mover_interface_manager.create(interface)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface(
                interface_name[:32])),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        interface = {
            'name': interface_name[:32],
            'ipAddress': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'vlanid': six.text_type(self.mover.vlan_id),
            'netMask': self.mover.net_mask,
            'device': self.mover.device_name,
        }
        exp_interface = mover_interface.MoverInterface(
            self.mover_interface_manager, interface)
        self.assertEqual(exp_interface, mi)

    def test_create_mover_interface_with_lazy_load(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_succeed())
        self.hook.append(self.mover.resp_get_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': self.mover.interface_name1,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        mi = self.mover_interface_manager.create(interface)
        self.assertEqual('IPv4', mi.ip_version)
        self.assertEqual('true', mi.up)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface(
                self.mover.interface_name1)),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        interface = {
            'name': self.mover.interface_name1,
            'ipAddress': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'vlanid': six.text_type(self.mover.vlan_id),
            'netMask': self.mover.net_mask,
            'device': self.mover.device_name,
            'up': 'true',
            'ipVersion': 'IPv4',
        }
        exp_interface = mover_interface.MoverInterface(
            self.mover_interface_manager, interface)
        self.assertEqual(exp_interface, mi)

    @ddt.data(
        fakes.MoverTestData().resp_create_interface_but_name_already_exist(),
        fakes.MoverTestData().resp_create_interface_but_ip_already_exist())
    def test_create_mover_interface_name_already_exist(self, xml_resp):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(xml_resp)

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': self.mover.interface_name1,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        mi = self.mover_interface_manager.create(interface)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        interface = {
            'name': self.mover.interface_name1,
            'ipAddress': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'vlanid': six.text_type(self.mover.vlan_id),
            'netMask': self.mover.net_mask,
            'device': self.mover.device_name,
        }
        exp_interface = mover_interface.MoverInterface(
            self.mover_interface_manager, interface)
        self.assertEqual(exp_interface, mi)

    @ddt.data(fakes.MoverTestData().resp_task_succeed(),
              fakes.MoverTestData().resp_task_error())
    def test_create_mover_interface_with_conflict_vlan_id(self, xml_resp):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(
            self.mover.resp_create_interface_with_conflicted_vlan_id())
        self.hook.append(xml_resp)

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': self.mover.interface_name1,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        self.assertRaises(VNXBackendError,
                          self.mover_interface_manager.create,
                          interface)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface()),
            mock.call(self.mover.req_delete_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_create_mover_interface_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': self.mover.interface_name1,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        mi = self.mover_interface_manager.create(interface)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        interface = {
            'name': self.mover.interface_name1,
            'ipAddress': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'vlanid': six.text_type(self.mover.vlan_id),
            'netMask': self.mover.net_mask,
            'device': self.mover.device_name,
        }
        exp_interface = mover_interface.MoverInterface(
            self.mover_interface_manager, interface)
        self.assertEqual(exp_interface, mi)

    def test_create_mover_interface_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_error())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': self.mover.interface_name1,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        self.assertRaises(VNXBackendError,
                          self.mover_interface_manager.create,
                          interface)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @ddt.data(fakes.MoverTestData().interface_name1,
              fakes.MoverTestData().long_interface_name)
    def test_get_mover_interface(self, interface_name):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_get_succeed())
        self.hook.append(self.mover.resp_get_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = self.mover_interface_manager.get(
            name=interface_name,
            mover_name=self.mover.mover_name)
        property_map = [
            'name',
            'mover_name',
            'device',
            'ip_addr',
            'ip_version',
            'net_mask',
            'up',
            'vlan_id',
        ]
        for prop in property_map:
            self.assertIn(prop, interface.__dict__)

        self.mover_interface_manager.get(
            name=interface_name,
            mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get()),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mover_interface_not_found(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_get_without_value())
        self.hook.append(self.mover.resp_get_error())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.mover_interface_manager.get,
                          name=self.mover.interface_name1,
                          mover_name=self.mover.mover_name)

        self.assertRaises(ObjectNotFound,
                          self.mover_interface_manager.get,
                          name=self.mover.interface_name1,
                          mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get()),
            mock.call(self.mover.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mover_interface(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mover_interface_manager.delete(
            ip_addr=self.mover.ip_address1,
            mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_delete_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mover_interface_but_nonexistent(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_delete_interface_but_nonexistent())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mover_interface_manager.delete(
            ip_addr=self.mover.ip_address1,
            mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_delete_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_delete_mover_interface_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mover_interface_manager.delete(
            ip_addr=self.mover.ip_address1,
            mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_delete_interface()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_delete_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mover_interface_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_error())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mover_interface_manager.delete,
                          ip_addr=self.mover.ip_address1,
                          mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_delete_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_operations_with_vdm_resource(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mover.resp_task_succeed())
        self.hook.append(self.mover.resp_task_succeed())

        xml_connector = self.mover_interface_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        interface = {
            'name': self.mover.interface_name1,
            'device_name': self.mover.device_name,
            'ip': self.mover.ip_address1,
            'mover_name': self.mover.mover_name,
            'net_mask': self.mover.net_mask,
            'vlan_id': self.mover.vlan_id,
        }
        mi = self.mover_interface_manager.create(interface)

        mi.delete()

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_create_interface(
                self.mover.interface_name1[:32])),
            mock.call(self.mover.req_delete_interface()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)
