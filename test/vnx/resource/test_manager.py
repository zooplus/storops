# coding=utf-8
from __future__ import unicode_literals

import unittest

from test.vnx.resource.fakes import mock_ssh_connector
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import nas_pool, filesystem, mover, vdm, \
    mover_interface, dns_domain, mount_point, filesystem_snapshot, \
    cifs_server, cifs_share, manager, nfs_share

from test.vnx.resource import fakes
from vnxCliApi.exception import VNXBackendError

__author__ = 'Cedric Zhuang'


class VNXFileClientTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        self.storage_manager = manager.VNXFileClient(
            host, username, password)

    def test_get_object_manager(self):
        class_map = {
            'pool': nas_pool.PoolManager,
            'filesystem': filesystem.FileSystemManager,
            'mover_ref': mover.MoverRefManager,
            'mover': mover.MoverManager,
            'vdm': vdm.VDMManager,
            'mover_interface': mover_interface.MoverInterfaceManager,
            'dns_domain': dns_domain.DNSDomainManager,
            'mount': mount_point.MountPointManager,
            'snapshot': filesystem_snapshot.SnapshotManager,
            'cifs_server': cifs_server.CIFSServerManager,
            'cifs_share': cifs_share.CIFSShareManager,
            'nfs_share': nfs_share.NFSShareManager,
        }

        for manager_type, class_name in class_map.items():
            object_manager = self.storage_manager.get_object_manager(
                manager_type)
            self.assertIsInstance(object_manager, class_name)

    def test_get_object_manager_with_invalid_type(self):
        self.assertRaises(
            VNXBackendError,
            self.storage_manager.get_object_manager,
            'fake_type')
