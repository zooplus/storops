# coding=utf-8
from __future__ import unicode_literals

import unittest

import mock

from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import manager

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx.resource import mount_point

__author__ = 'Jay Xu'


class MountPointTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.StorageManager(host, username, password)
        self.mountpoint_manager = mount_point.MountPointManager(
            storage_manager)

        self.vdm = fakes.VDMTestData()
        self.fs = fakes.FileSystemTestData()
        self.mover = fakes.MoverTestData()
        self.mount = fakes.MountPointTestData()

    def test_create_mount_point_on_vdm(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.create(mount_path=self.mount.path,
                                       fs_name=self.fs.filesystem_name,
                                       mover_name=self.vdm.vdm_name,
                                       is_vdm=True)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_create(self.vdm.vdm_id, True)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_mount_point_on_mover(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.create(
            mount_path=self.mount.path,
            fs_name=self.fs.filesystem_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_create(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_mount_point_but_already_exist(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_create_but_already_exist())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.create(mount_path=self.mount.path,
                                       fs_name=self.fs.filesystem_name,
                                       mover_name=self.vdm.vdm_name,
                                       is_vdm=True)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_create(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_create_mount_point_invalid_mover_id(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.create(mount_path=self.mount.path,
                                       fs_name=self.fs.filesystem_name,
                                       mover_name=self.mover.mover_name,
                                       is_vdm=False)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_create(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_create(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_mount_point_with_error(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_task_error())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mountpoint_manager.create,
                          mount_path=self.mount.path,
                          fs_name=self.fs.filesystem_name,
                          mover_name=self.vdm.vdm_name,
                          is_vdm=True)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_create(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mount_point_on_vdm(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.delete(mount_path=self.mount.path,
                                       mover_name=self.vdm.vdm_name,
                                       is_vdm=True)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mount_point_on_mover(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.delete(mount_path=self.mount.path,
                                       mover_name=self.mover.mover_name,
                                       is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_delete(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mount_point_but_nonexistent(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_delete_but_nonexistent())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.delete(mount_path=self.mount.path,
                                       mover_name=self.vdm.vdm_name,
                                       is_vdm=True)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_delete_mount_point_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.mountpoint_manager.delete(mount_path=self.mount.path,
                                       mover_name=self.mover.mover_name,
                                       is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_delete(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_delete(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_mount_point_with_error(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_task_error())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mountpoint_manager.delete,
                          mount_path=self.mount.path,
                          mover_name=self.vdm.vdm_name,
                          is_vdm=True)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mount_point(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_get_succeed(self.vdm.vdm_id))
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_get_succeed(self.mover.mover_id,
                                                     False))

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        mount_point = self.mountpoint_manager.get(
            self.mount.path, mover_name=self.vdm.vdm_name)
        property_map = [
            'path',
            'filesystem_id',
            'mover_name',
            'mover_id',
            'is_vdm',
        ]
        for prop in property_map:
            self.assertIn(prop, mount_point.__dict__)

        mount_point = self.mountpoint_manager.get(
            self.mount.path, mover_name=self.mover.mover_name, is_vdm=False)
        property_map = [
            'path',
            'filesystem_id',
            'mover_name',
            'mover_id',
            'is_vdm',
        ]
        for prop in property_map:
            self.assertIn(prop, mount_point.__dict__)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_get(self.vdm.vdm_id)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mount_point_but_not_found(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_get_without_value())
        self.hook.append(self.mount.resp_get_succeed(self.mover.mover_id,
                                                     False))

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.mountpoint_manager.get,
                          self.mount.path,
                          mover_name=self.mover.mover_name,
                          is_vdm=False)

        self.assertRaises(ObjectNotFound,
                          self.mountpoint_manager.get,
                          'fake_path',
                          mover_name=self.mover.mover_name,
                          is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_get(self.mover.mover_id, False)),
            mock.call(self.mount.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_get_mount_point_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_get_succeed(self.mover.mover_id,
                                                     False))

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        mount_point = self.mountpoint_manager.get(
            self.mount.path, mover_name=self.mover.mover_name, is_vdm=False)

        property_map = [
            'path',
            'filesystem_id',
            'mover_name',
            'mover_id',
            'is_vdm',
        ]
        for prop in property_map:
            self.assertIn(prop, mount_point.__dict__)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_get(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_mount_point_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.mount.resp_get_error())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.mountpoint_manager.get,
                          self.mount.path,
                          mover_name=self.mover.mover_name,
                          is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mount.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_operations_with_mount_point_resource(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.mount.resp_task_succeed())
        self.hook.append(self.mount.resp_task_succeed())

        xml_connector = self.mountpoint_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        mountpoint = self.mountpoint_manager.create(
            mount_path=self.mount.path,
            fs_name=self.fs.filesystem_name,
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        mountpoint.delete()

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.mount.req_create(self.vdm.vdm_id, True)),
            mock.call(self.mount.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)
