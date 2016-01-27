# coding=utf-8
from __future__ import unicode_literals

import unittest

import mock

from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import cifs_server

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import VNXBackendError
from vnxCliApi.vnx.resource import nas_client

__author__ = 'Jay Xu'


class CIFSServerTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()
        self.ssh_hook = utils.SSHSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = nas_client.VNXNasClient(host, username, password)
        self.server_manager = cifs_server.CIFSServerManager(storage_manager)

        self.mover = fakes.MoverTestData()
        self.vdm = fakes.VDMTestData()
        self.cifs_server = fakes.CIFSServerTestData()

    def test_create_cifs_server(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())
        self.hook.append(self.cifs_server.resp_task_error())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True))

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create CIFS server on mover
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.mover.mover_name,
            'is_vdm': False,
        }
        self.server_manager.create(**cifs_server_args)

        # Create CIFS server on VDM
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
            'is_vdm': True,
        }
        self.server_manager.create(**cifs_server_args)

        # Create CIFS server on VDM
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
            'is_vdm': True,
        }
        self.server_manager.create(**cifs_server_args)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_create(self.mover.mover_id, False)),
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_create(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_create(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_cifs_server_already_exist(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_task_error())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True))

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create CIFS server on VDM
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
            'is_vdm': True,
        }
        self.server_manager.create(**cifs_server_args)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_create(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
        ]

        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_create_cifs_server_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create CIFS server on mover
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.mover.mover_name,
            'is_vdm': False,
        }
        self.server_manager.create(**cifs_server_args)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_create(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_create(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_cifs_server_with_error(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_task_error())
        self.hook.append(self.cifs_server.resp_get_error())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create CIFS server on VDM
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
            'is_vdm': True,
        }
        self.assertRaises(VNXBackendError,
                          self.server_manager.create,
                          **cifs_server_args)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_create(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_all_cifs_server(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True))
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True))

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_list = self.server_manager.get_all(self.vdm.vdm_name)
        for server_name, server in cifs_server_list.items():
            self.assertEqual(self.vdm.vdm_name, server.mover_name)

        # Get CIFS server from the cache
        cifs_server_list = self.server_manager.get_all(self.vdm.vdm_name)
        for server_name, server in cifs_server_list.items():
            self.assertEqual(self.vdm.vdm_name, server.mover_name)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_get_all_cifs_server_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.mover.mover_id, is_vdm=False, join_domain=True))

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_list = self.server_manager.get_all(self.mover.mover_name,
                                                       False)
        for server_name, server in cifs_server_list.items():
            self.assertEqual(self.mover.mover_name, server.mover_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_get(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_cifs_server(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True))

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        server = self.server_manager.get(
            comp_name=self.cifs_server.cifs_server_name,
            mover_name=self.vdm.vdm_name)
        property_map = {
            'name',
            'comp_name',
            'aliases',
            'domain',
            'domain_joined',
            'interfaces',
            'mover_name',
            'mover_id',
            'is_vdm',
            'type',
        }
        for prop in property_map:
            self.assertIn(prop, server.__dict__)

        self.server_manager.get(comp_name=self.cifs_server.cifs_server_name,
                                mover_name=self.vdm.vdm_name)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_modify_cifs_server(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name[-14:],
            'domain_joined': True,
            'username': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.mover.mover_name,
            'is_vdm': False,
        }
        self.server_manager.modify(**cifs_server_args)

        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name[-14:],
            'domain_joined': False,
            'username': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
        }
        self.server_manager.modify(**cifs_server_args)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.mover.mover_id, is_vdm=False, join_domain=True)),
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_modify_cifs_server_but_unjoin_domain(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_modify_but_unjoin_domain())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name[-14:],
            'domain_joined': False,
            'username': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
        }

        self.server_manager.modify(**cifs_server_args)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_modify_cifs_server_but_already_join_domain(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(
            self.cifs_server.resp_modify_but_already_join_domain())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name[-14:],
            'domain_joined': True,
            'username': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
        }

        self.server_manager.modify(**cifs_server_args)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_modify_cifs_server_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name[-14:],
            'domain_joined': True,
            'username': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.mover.mover_name,
            'is_vdm': False,
        }
        self.server_manager.modify(**cifs_server_args)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.mover.mover_id, is_vdm=False, join_domain=True)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.mover.mover_id, is_vdm=False, join_domain=True)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_modify_cifs_server_with_error(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_task_error())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name[-14:],
            'domain_joined': False,
            'username': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
        }
        self.assertRaises(VNXBackendError,
                          self.server_manager.modify,
                          **cifs_server_args)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_server(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.mover.mover_id, is_vdm=False, join_domain=True))
        self.hook.append(self.cifs_server.resp_task_succeed())
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=False))
        self.hook.append(self.cifs_server.resp_task_succeed())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.server_manager.delete(
            comp_name=self.cifs_server.cifs_server_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        self.server_manager.delete(
            comp_name=self.cifs_server.cifs_server_name,
            mover_name=self.vdm.vdm_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_get(self.mover.mover_id, False)),
            mock.call(self.cifs_server.req_delete(self.mover.mover_id, False)),
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_server_but_not_found(self):
        self.hook.append(self.mover.resp_get_without_value())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_get_without_value())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.server_manager.delete(
            comp_name=self.cifs_server.cifs_server_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        self.server_manager.delete(
            comp_name=self.cifs_server.cifs_server_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_server_but_fail_to_get_cifs_server(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_get_error())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.server_manager.delete,
                          comp_name=self.cifs_server.cifs_server_name,
                          mover_name=self.mover.mover_name,
                          is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_get(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_server_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.mover.mover_id, is_vdm=False, join_domain=True))
        self.hook.append(self.cifs_server.resp_task_error())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.server_manager.delete,
                          comp_name=self.cifs_server.cifs_server_name,
                          mover_name=self.mover.mover_name,
                          is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_server.req_get(self.mover.mover_id, False)),
            mock.call(self.cifs_server.req_delete(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_operations_with_cifs_server_resource(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())
        self.hook.append(self.cifs_server.resp_get_succeed(
            mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=True))
        self.hook.append(self.cifs_server.resp_task_succeed())
        self.hook.append(self.cifs_server.resp_task_succeed())

        xml_connector = self.server_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        # Create CIFS server on VDM
        cifs_server_args = {
            'name': self.cifs_server.cifs_server_name,
            'interface_ip': self.cifs_server.ip_address1,
            'domain_name': self.cifs_server.domain_name,
            'user_name': self.cifs_server.domain_user,
            'password': self.cifs_server.domain_password,
            'mover_name': self.vdm.vdm_name,
            'is_vdm': True,
        }
        server = self.server_manager.create(**cifs_server_args)

        server.modify(username=self.cifs_server.domain_user,
                      password=self.cifs_server.domain_password)

        server.delete()

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_server.req_create(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_get(self.vdm.vdm_id)),
            mock.call(self.cifs_server.req_modify(
                mover_id=self.vdm.vdm_id, is_vdm=True, join_domain=False)),
            mock.call(self.cifs_server.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)
