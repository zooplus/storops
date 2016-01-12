# coding=utf-8
from __future__ import unicode_literals

import unittest

import ddt
import mock

from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import filesystem

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx.resource import manager

__author__ = 'Jay Xu'


@ddt.ddt
class FileSystemTestCase(unittest.TestCase):
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
        self.filesystem_manager = filesystem.FileSystemManager(
            storage_manager)

        self.vdm = fakes.VDMTestData()
        self.mover = fakes.MoverTestData()
        self.pool = fakes.PoolTestData()
        self.fs = fakes.FileSystemTestData()
        self.snap = fakes.SnapshotTestData()
        self.mount = fakes.MountPointTestData()

    def test_create_file_system_on_vdm(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.fs.resp_task_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.create(
            name=self.fs.filesystem_name,
            size=self.fs.filesystem_size,
            pool_name=self.pool.pool_name,
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.fs.req_create_on_vdm()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        exp_data = {
            'name': self.fs.filesystem_name,
            'volumeSize': self.fs.filesystem_size,
        }
        exp_filesystem = filesystem.FileSystem(self.filesystem_manager,
                                               exp_data)
        self.assertEqual(exp_filesystem, fs)

    def test_create_file_system_on_mover(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.fs.resp_task_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.create(
            name=self.fs.filesystem_name,
            size=self.fs.filesystem_size,
            pool_name=self.pool.pool_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.fs.req_create_on_mover()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        exp_data = {
            'name': self.fs.filesystem_name,
            'volumeSize': self.fs.filesystem_size,
        }
        exp_filesystem = filesystem.FileSystem(self.filesystem_manager,
                                               exp_data)
        self.assertEqual(exp_filesystem, fs)

    def test_create_file_system_but_already_exist(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.fs.resp_create_but_already_exist())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.create(
            name=self.fs.filesystem_name,
            size=self.fs.filesystem_size,
            pool_name=self.pool.pool_name,
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.fs.req_create_on_vdm()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        exp_data = {
            'name': self.fs.filesystem_name,
            'volumeSize': self.fs.filesystem_size,
        }
        exp_filesystem = filesystem.FileSystem(self.filesystem_manager,
                                               exp_data)
        self.assertEqual(exp_filesystem, fs)

    @patch_retry
    def test_create_file_system_invalid_mover_id(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.fs.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.fs.resp_task_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.create(
            name=self.fs.filesystem_name,
            size=self.fs.filesystem_size,
            pool_name=self.pool.pool_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.fs.req_create_on_mover()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.fs.req_create_on_mover()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        exp_data = {
            'name': self.fs.filesystem_name,
            'volumeSize': self.fs.filesystem_size,
        }
        exp_filesystem = filesystem.FileSystem(self.filesystem_manager,
                                               exp_data)
        self.assertEqual(exp_filesystem, fs)

    def test_create_file_system_with_error(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.fs.resp_task_error())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.filesystem_manager.create,
                          name=self.fs.filesystem_name,
                          size=self.fs.filesystem_size,
                          pool_name=self.pool.pool_name,
                          mover_name=self.vdm.vdm_name,
                          is_vdm=True)

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.fs.req_create_on_vdm()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_file_system(self):
        self.hook.append(self.fs.resp_get_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.get(self.fs.filesystem_name)
        self.assertIn(self.fs.filesystem_name,
                      self.filesystem_manager.filesystem_map)
        property_map = [
            'name',
            'id',
            'type',
            'size',
            'pools',
            'storages',
            'internal_use',
            'volume',
            'policies',
        ]
        for prop in property_map:
            self.assertIn(prop, fs.__dict__)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    @ddt.data(fakes.FileSystemTestData().resp_get_but_not_found(),
              fakes.FileSystemTestData().resp_get_without_value(),
              fakes.FileSystemTestData().resp_get_but_not_found())
    def test_get_file_system_but_not_found(self, xml_resp):
        self.hook.append(xml_resp)

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.filesystem_manager.get,
                          self.fs.filesystem_name)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_file_system_with_error(self):
        self.hook.append(self.fs.resp_get_error())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.filesystem_manager.get,
                          self.fs.filesystem_name)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_file_system_but_miss_property(self):
        self.hook.append(self.fs.resp_get_but_miss_property())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.get(self.fs.filesystem_name)
        self.assertIn(self.fs.filesystem_name,
                      self.filesystem_manager.filesystem_map)
        property_map = [
            'name',
            'id',
            'type',
            'size',
            'pools',
            'storages',
            'internal_use',
            'volume',
        ]
        for prop in property_map:
            self.assertIn(prop, fs.__dict__)

        self.assertNotIn('filesystem', fs.__dict__)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_file_system(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.fs.resp_task_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.filesystem_manager.delete(self.fs.filesystem_name)
        self.assertNotIn(self.fs.filesystem_name,
                         self.filesystem_manager.filesystem_map)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.fs.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_file_system_but_not_found(self):
        self.hook.append(self.fs.resp_get_but_not_found())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.filesystem_manager.delete(self.fs.filesystem_name)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_file_system_but_get_file_system_error(self):
        self.hook.append(self.fs.resp_get_error())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.filesystem_manager.delete,
                          self.fs.filesystem_name)

        self.assertNotIn(self.fs.filesystem_name,
                         self.filesystem_manager.filesystem_map)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_file_system_with_error(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.fs.resp_delete_but_failed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.filesystem_manager.delete,
                          self.fs.filesystem_name)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.fs.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        self.assertIn(self.fs.filesystem_name,
                      self.filesystem_manager.filesystem_map)

    def test_extend_file_system(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.fs.resp_task_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        filesystem_name = self.fs.filesystem_name

        self.filesystem_manager.extend(
            name=filesystem_name,
            pool_name=self.pool.pool_name,
            new_size=self.fs.filesystem_new_size)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.pool.req_get()),
            mock.call(self.fs.req_extend()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        self.assertEqual(
            self.fs.filesystem_new_size,
            self.filesystem_manager.filesystem_map[filesystem_name].size)

    def test_extend_file_system_but_not_found(self):
        self.hook.append(self.fs.resp_get_but_not_found())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.filesystem_manager.extend,
                          name=self.fs.filesystem_name,
                          pool_name=self.fs.pool_name,
                          new_size=self.fs.filesystem_new_size)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_extend_file_system_with_small_size(self):
        self.hook.append(self.fs.resp_get_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.filesystem_manager.extend,
                          name=self.fs.filesystem_name,
                          pool_name=self.pool.pool_name,
                          new_size=1)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_extend_file_system_with_same_size(self):
        self.hook.append(self.fs.resp_get_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.filesystem_manager.extend(
            name=self.fs.filesystem_name,
            pool_name=self.pool.pool_name,
            new_size=self.fs.filesystem_size)

        expected_calls = [mock.call(self.fs.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_extend_file_system_with_error(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.fs.resp_extend_but_error())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.filesystem_manager.extend,
                          name=self.fs.filesystem_name,
                          pool_name=self.pool.pool_name,
                          new_size=self.fs.filesystem_new_size)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.pool.req_get()),
            mock.call(self.fs.req_extend()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_filesystem_from_snapshot(self):
        self.ssh_hook.append()
        self.ssh_hook.append()
        self.ssh_hook.append(self.fs.output_copy_ckpt)
        self.ssh_hook.append(self.fs.output_info())
        self.ssh_hook.append()
        self.ssh_hook.append()
        self.ssh_hook.append()

        ssh_connector = self.filesystem_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.filesystem_manager.create_from_snapshot(
            self.fs.filesystem_name,
            self.snap.src_snap_name,
            self.fs.src_fileystems_name,
            self.pool.pool_name,
            self.vdm.vdm_name,
            self.mover.interconnect_id, )

        ssh_calls = [
            mock.call(self.fs.cmd_create_from_ckpt(), check_exit_code=False),
            mock.call(self.mount.cmd_server_mount('ro'),
                      check_exit_code=False),
            mock.call(self.fs.cmd_copy_ckpt(), check_exit_code=True),
            mock.call(self.fs.cmd_nas_fs_info(), check_exit_code=False),
            mock.call(self.mount.cmd_server_umount(), check_exit_code=False),
            mock.call(self.fs.cmd_delete(), check_exit_code=False),
            mock.call(self.mount.cmd_server_mount('rw'),
                      check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_create_filesystem_from_snapshot_with_error(self):
        self.ssh_hook.append()
        self.ssh_hook.append()
        self.ssh_hook.append(ex=SSHExecutionError(
            stdout=self.fs.fake_output, stderr=None))
        self.ssh_hook.append(self.fs.output_info())
        self.ssh_hook.append()
        self.ssh_hook.append()
        self.ssh_hook.append()

        ssh_connector = self.filesystem_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.filesystem_manager.create_from_snapshot(
            self.fs.filesystem_name,
            self.snap.src_snap_name,
            self.fs.src_fileystems_name,
            self.pool.pool_name,
            self.vdm.vdm_name,
            self.mover.interconnect_id, )

        ssh_calls = [
            mock.call(self.fs.cmd_create_from_ckpt(), check_exit_code=False),
            mock.call(self.mount.cmd_server_mount('ro'),
                      check_exit_code=False),
            mock.call(self.fs.cmd_copy_ckpt(), check_exit_code=True),
            mock.call(self.fs.cmd_nas_fs_info(), check_exit_code=False),
            mock.call(self.mount.cmd_server_umount(), check_exit_code=False),
            mock.call(self.fs.cmd_delete(), check_exit_code=False),
            mock.call(self.mount.cmd_server_mount('rw'),
                      check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_operations_with_filesystem_resource(self):
        self.hook.append(self.pool.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.fs.resp_task_succeed())
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.fs.resp_task_succeed())

        xml_connector = self.filesystem_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        fs = self.filesystem_manager.create(
            name=self.fs.filesystem_name,
            size=self.fs.filesystem_size,
            pool_name=self.pool.pool_name,
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        exp_data = {
            'name': self.fs.filesystem_name,
            'volumeSize': self.fs.filesystem_size,
        }
        exp_filesystem = filesystem.FileSystem(self.filesystem_manager,
                                               exp_data)
        self.assertEqual(exp_filesystem, fs)

        with mock.patch.object(filesystem.FileSystemManager,
                               'extend',
                               mock.Mock()):
            fs.extend(new_size=self.fs.filesystem_new_size)
            fs.extend(
                new_size=self.fs.filesystem_new_size,
                pool_name=self.pool.pool_name)

        fs.delete()

        expected_calls = [
            mock.call(self.pool.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.fs.req_create_on_vdm()),
            mock.call(self.fs.req_get()),
            mock.call(self.fs.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)
