# coding=utf-8
from __future__ import unicode_literals

import unittest

import ddt
import mock

from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import vdm

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx.resource import manager

__author__ = 'Jay Xu'


@ddt.ddt
class VDMTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()
        self.ssh_hook = utils.SSHSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.StorageManager(host, username, password)
        self.vdm_manager = vdm.VDMManager(storage_manager)

        self.vdm = fakes.VDMTestData()
        self.mover = fakes.MoverTestData()

    def test_create_vdm_(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_task_succeed())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        v = self.vdm_manager.create(self.vdm.vdm_name, self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        exp_vdm = vdm.VDM(self.vdm_manager, dict(name=self.vdm.vdm_name))
        self.assertEqual(exp_vdm, v)

    def test_create_vdm_with_lazy_load(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_task_succeed())
        self.hook.append(self.vdm.resp_get_succeed())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        vdm = self.vdm_manager.create(self.vdm.vdm_name, self.mover.mover_name)
        self.assertEqual(self.vdm.vdm_id, vdm.id)
        self.assertEqual(self.vdm.mover_id, vdm.host_mover_id)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
            mock.call(self.vdm.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_vdm_but_already_exist(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_create_but_already_exist())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create VDM which already exists.
        self.vdm_manager.create(self.vdm.vdm_name, self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_create_vdm_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_task_succeed())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create VDM with invalid mover ID
        self.vdm_manager.create(self.vdm.vdm_name, self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_vdm_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_task_error())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create VDM with invalid mover ID
        self.assertRaises(VNXBackendError,
                          self.vdm_manager.create,
                          name=self.vdm.vdm_name,
                          mover_name=self.mover.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_vdm(self):
        self.hook.append(self.vdm.resp_get_succeed())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        vdm = self.vdm_manager.get(self.vdm.vdm_name)
        self.assertIn(self.vdm.vdm_name, self.vdm_manager.vdm_map)
        property_map = [
            'name',
            'id',
            'state',
            'host_mover_id',
        ]
        for prop in property_map:
            self.assertIn(prop, vdm.__dict__)

        expected_calls = [mock.call(self.vdm.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    @ddt.data(fakes.VDMTestData().resp_get_without_value(),
              fakes.VDMTestData().resp_get_succeed('fake'))
    def test_get_vdm_but_not_found(self, xml_resp):
        self.hook.append(xml_resp)

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Get VDM which does not exist
        self.assertRaises(ObjectNotFound,
                          self.vdm_manager.get,
                          self.vdm.vdm_name)

        expected_calls = [mock.call(self.vdm.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_vdm_with_error(self):
        self.hook.append(self.vdm.resp_task_error())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Get VDM which does not exist
        self.assertRaises(VNXBackendError,
                          self.vdm_manager.get,
                          self.vdm.vdm_name)

        expected_calls = [mock.call(self.vdm.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_vdm(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.vdm.resp_task_succeed())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.vdm_manager.delete(self.vdm.vdm_name)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.vdm.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_vdm_but_not_found(self):
        self.hook.append(self.vdm.resp_get_but_not_found())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.vdm_manager.delete(self.vdm.vdm_name)

        expected_calls = [mock.call(self.vdm.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_vdm_but_failed_to_get_vdm(self):
        self.hook.append(self.vdm.resp_get_error())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.vdm_manager.delete,
                          self.vdm.vdm_name)

        expected_calls = [mock.call(self.vdm.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_vdm_with_error(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.vdm.resp_task_error())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.vdm_manager.delete,
                          self.vdm.vdm_name)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.vdm.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_attach_detach_nfs_interface(self):
        self.ssh_hook.append()
        self.ssh_hook.append()

        ssh_connector = self.vdm_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.vdm_manager.attach_nfs_interface(self.vdm.vdm_name,
                                              self.mover.interface_name2)
        self.vdm_manager.detach_nfs_interface(self.vdm.vdm_name,
                                              self.mover.interface_name2)

        ssh_calls = [
            mock.call(self.vdm.cmd_attach_nfs_interface(),
                      check_exit_code=False),
            mock.call(self.vdm.cmd_detach_nfs_interface(),
                      check_exit_code=True),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_detach_nfs_interface_with_error(self):
        self.ssh_hook.append(ex=SSHExecutionError(
            stdout=self.vdm.fake_output))
        self.ssh_hook.append(self.vdm.output_get_interfaces(
            self.mover.interface_name2))
        self.ssh_hook.append(ex=SSHExecutionError(
            stdout=self.vdm.fake_output))
        self.ssh_hook.append(self.vdm.output_get_interfaces(
            nfs_interface=fakes.FakeData.interface_name1))

        ssh_connector = self.vdm_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.vdm_manager.detach_nfs_interface,
                          self.vdm.vdm_name,
                          self.mover.interface_name2)

        self.vdm_manager.detach_nfs_interface(self.vdm.vdm_name,
                                              self.mover.interface_name2)

        ssh_calls = [
            mock.call(self.vdm.cmd_detach_nfs_interface(),
                      check_exit_code=True),
            mock.call(self.vdm.cmd_get_interfaces(), check_exit_code=False),
            mock.call(self.vdm.cmd_detach_nfs_interface(),
                      check_exit_code=True),
            mock.call(self.vdm.cmd_get_interfaces(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_get_cifs_nfs_interface(self):
        self.ssh_hook.append(self.vdm.output_get_interfaces())

        ssh_connector = self.vdm_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        interfaces = self.vdm_manager.get_interfaces(self.vdm.vdm_name)
        self.assertIsNotNone(interfaces['cifs'])
        self.assertIsNotNone(interfaces['nfs'])

        ssh_calls = [
            mock.call(self.vdm.cmd_get_interfaces(), check_exit_code=False)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_operations_with_vdm_resource(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.vdm.resp_task_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.vdm.resp_task_succeed())

        xml_connector = self.vdm_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.ssh_hook.append()
        self.ssh_hook.append(self.vdm.output_get_interfaces())
        self.ssh_hook.append()

        ssh_connector = self.vdm_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        v = self.vdm_manager.create(self.vdm.vdm_name, self.mover.mover_name)

        exp_vdm = vdm.VDM(self.vdm_manager, dict(name=self.vdm.vdm_name))
        self.assertEqual(exp_vdm, v)

        v.attach_nfs_interface(self.mover.interface_name2)
        v.get_interfaces()
        v.detach_nfs_interface(self.mover.interface_name2)
        v.delete()

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.vdm.req_create()),
            mock.call(self.vdm.req_get()),
            mock.call(self.vdm.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        ssh_calls = [
            mock.call(self.vdm.cmd_attach_nfs_interface(),
                      check_exit_code=False),
            mock.call(self.vdm.cmd_get_interfaces(), check_exit_code=False),
            mock.call(self.vdm.cmd_detach_nfs_interface(),
                      check_exit_code=True),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)
