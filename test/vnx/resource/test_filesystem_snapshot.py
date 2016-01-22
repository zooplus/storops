# coding=utf-8
from __future__ import unicode_literals

import unittest

import mock

from test.vnx.resource.fakes import mock_ssh_connector, mock_xml_api
from vnxCliApi.vnx.resource import manager

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx.resource import filesystem_snapshot

__author__ = 'Jay Xu'


class SnapshotTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.VNXFileClient(host, username, password)
        self.snapshot_manager = filesystem_snapshot.SnapshotManager(
            storage_manager)

        self.fs = fakes.FileSystemTestData()
        self.snap = fakes.SnapshotTestData()
        self.pool = fakes.PoolTestData()

    def test_create_snapshot(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.snap.resp_task_succeed())
        self.hook.append(self.snap.resp_get_succeed())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.snapshot_manager.create(name=self.snap.snapshot_name,
                                     fs_name=self.fs.filesystem_name,
                                     pool_id=self.pool.pool_id)

        self.snapshot_manager.get(self.snap.snapshot_name)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.snap.req_create()),
            mock.call(self.snap.req_get())
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_snapshot_but_already_exist(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.snap.resp_create_but_already_exist())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.snapshot_manager.create(name=self.snap.snapshot_name,
                                     fs_name=self.fs.filesystem_name,
                                     pool_id=self.pool.pool_id,
                                     ckpt_size=self.snap.snapshot_size)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.snap.req_create_with_size()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_snapshot_with_error(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.snap.resp_task_error())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.snapshot_manager.create,
                          name=self.snap.snapshot_name,
                          fs_name=self.fs.filesystem_name,
                          pool_id=self.pool.pool_id,
                          ckpt_size=self.snap.snapshot_size)

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.snap.req_create_with_size()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_snapshot(self):
        self.hook.append(self.snap.resp_get_succeed())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        snapshot = self.snapshot_manager.get(self.snap.snapshot_name)
        self.assertIn(self.snap.snapshot_name,
                      self.snapshot_manager.snapshot_map)
        property_map = [
            'name',
            'id',
            'fs_id',
            'state',
        ]
        for prop in property_map:
            self.assertIn(prop, snapshot.__dict__)

        expected_calls = [mock.call(self.snap.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_snapshot_but_not_found(self):
        self.hook.append(self.snap.resp_get_without_value())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(ObjectNotFound,
                          self.snapshot_manager.get,
                          self.snap.snapshot_name)

        expected_calls = [mock.call(self.snap.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_snapshot_with_error(self):
        self.hook.append(self.snap.resp_get_error())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.snapshot_manager.get,
                          self.snap.snapshot_name)

        expected_calls = [mock.call(self.snap.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_snapshot(self):
        self.hook.append(self.snap.resp_get_succeed())
        self.hook.append(self.snap.resp_task_succeed())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.snapshot_manager.delete(self.snap.snapshot_name)
        self.assertNotIn(self.snap.snapshot_name,
                         self.snapshot_manager.snapshot_map)

        expected_calls = [
            mock.call(self.snap.req_get()),
            mock.call(self.snap.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_snapshot_failed_to_get_snapshot(self):
        self.hook.append(self.snap.resp_get_error())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.snapshot_manager.delete,
                          self.snap.snapshot_name)

        expected_calls = [mock.call(self.snap.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_snapshot_but_not_found(self):
        self.hook.append(self.snap.resp_get_without_value())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.snapshot_manager.delete(self.snap.snapshot_name)
        self.assertNotIn(self.snap.snapshot_name,
                         self.snapshot_manager.snapshot_map)

        expected_calls = [mock.call(self.snap.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_snapshot_with_error(self):
        self.hook.append(self.snap.resp_get_succeed())
        self.hook.append(self.snap.resp_task_error())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.snapshot_manager.delete,
                          self.snap.snapshot_name)

        expected_calls = [
            mock.call(self.snap.req_get()),
            mock.call(self.snap.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_operations_with_snapshot_resource(self):
        self.hook.append(self.fs.resp_get_succeed())
        self.hook.append(self.snap.resp_task_succeed())
        self.hook.append(self.snap.resp_get_succeed())
        self.hook.append(self.snap.resp_task_succeed())

        xml_connector = self.snapshot_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        snapshot = self.snapshot_manager.create(
            name=self.snap.snapshot_name,
            fs_name=self.fs.filesystem_name,
            pool_id=self.pool.pool_id)

        snapshot.delete()

        expected_calls = [
            mock.call(self.fs.req_get()),
            mock.call(self.snap.req_create()),
            mock.call(self.snap.req_get()),
            mock.call(self.snap.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)
