# coding=utf-8
from __future__ import unicode_literals

import unittest

import ddt
import mock

from test import utils
from test.vnx.resource import fakes
from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXBackendError
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import cifs_share
from vnxCliApi.vnx.resource import nas_client

__author__ = 'Jay Xu'


@ddt.ddt
class CIFSShareTestCase(unittest.TestCase):
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
        self.share_manager = cifs_share.CIFSShareManager(storage_manager)

        self.vdm = fakes.VDMTestData()
        self.mover = fakes.MoverTestData()
        self.cifs_share = fakes.CIFSShareTestData()
        self.cifs_server = fakes.CIFSServerTestData()

    def test_create_cifs_share(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.share_manager.create(
            name=self.cifs_share.share_name,
            server_name=self.cifs_share.cifs_server_name[-14:],
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        self.share_manager.create(
            name=self.cifs_share.share_name,
            server_name=self.cifs_share.cifs_server_name[-14:],
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_share.req_create(self.vdm.vdm_id)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_share.req_create(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_create_cifs_share_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_share.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.share_manager.create(
            name=self.cifs_share.share_name,
            server_name=self.cifs_share.cifs_server_name[-14:],
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_share.req_create(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_share.req_create(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_cifs_share_with_error(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_share.resp_task_error())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.create,
                          name=self.cifs_share.share_name,
                          server_name=self.cifs_share.cifs_server_name[-14:],
                          mover_name=self.vdm.vdm_name,
                          is_vdm=True)

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_share.req_create(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_share(self):
        self.hook.append(self.cifs_share.resp_get_succeed(self.vdm.vdm_id))
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())
        self.hook.append(self.cifs_share.resp_get_succeed(self.mover.mover_id,
                                                          False))
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.share_manager.delete(
            name=self.cifs_share.share_name,
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        self.share_manager.delete(
            name=self.cifs_share.share_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.cifs_share.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_share.req_delete(self.vdm.vdm_id)),
            mock.call(self.cifs_share.req_get()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_share.req_delete(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_share_not_found(self):
        self.hook.append(self.cifs_share.resp_get_error())
        self.hook.append(self.cifs_share.resp_get_without_value())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.delete,
                          name=self.cifs_share.share_name,
                          mover_name=self.vdm.vdm_name,
                          is_vdm=True)

        self.share_manager.delete(
            name=self.cifs_share.share_name,
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        expected_calls = [
            mock.call(self.cifs_share.req_get()),
            mock.call(self.cifs_share.req_get()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_delete_cifs_share_invalid_mover_id(self):
        self.hook.append(self.cifs_share.resp_get_succeed(self.mover.mover_id,
                                                          False))
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_share.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.share_manager.delete(
            name=self.cifs_share.share_name,
            mover_name=self.mover.mover_name,
            is_vdm=False)

        expected_calls = [
            mock.call(self.cifs_share.req_get()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_share.req_delete(self.mover.mover_id, False)),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.cifs_share.req_delete(self.mover.mover_id, False)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_cifs_share_with_error(self):
        self.hook.append(self.cifs_share.resp_get_succeed(self.vdm.vdm_id))
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_share.resp_task_error())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.delete,
                          name=self.cifs_share.share_name,
                          mover_name=self.vdm.vdm_name,
                          is_vdm=True)

        expected_calls = [
            mock.call(self.cifs_share.req_get()),
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_share.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_get_cifs_share(self):
        self.hook.append(self.cifs_share.resp_get_succeed(self.vdm.vdm_id))

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.share_manager.get(self.cifs_share.share_name)

        expected_calls = [mock.call(self.cifs_share.req_get())]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_disable_share_access(self):
        self.ssh_hook.append('Command succeeded')

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.disable_share_access(
            share_name=self.cifs_share.share_name,
            mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.cifs_share.cmd_disable_access(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_disable_share_access_with_error(self):
        self.ssh_hook.append(ex=SSHExecutionError(
            stdout=self.cifs_share.fake_output))

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.disable_share_access,
                          share_name=self.cifs_share.share_name,
                          mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.cifs_share.cmd_disable_access(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_allow_share_access(self):
        self.ssh_hook.append(self.cifs_share.output_allow_access())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.allow_share_access(
            mover_name=self.vdm.vdm_name,
            share_name=self.cifs_share.share_name,
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [mock.call(self.cifs_share.cmd_change_access(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_allow_share_access_duplicate_ACE(self):
        expt_dup_ace = SSHExecutionError(
            stdout=self.cifs_share.output_allow_access_but_duplicate_ace())
        self.ssh_hook.append(ex=expt_dup_ace)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.allow_share_access(
            mover_name=self.vdm.vdm_name,
            share_name=self.cifs_share.share_name,
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [mock.call(self.cifs_share.cmd_change_access(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_allow_share_access_with_error(self):
        expt_err = SSHExecutionError(
            self.cifs_share.fake_output)
        self.ssh_hook.append(ex=expt_err)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.allow_share_access,
                          mover_name=self.vdm.vdm_name,
                          share_name=self.cifs_share.share_name,
                          user_name=self.cifs_server.domain_user,
                          domain=self.cifs_server.domain_name,
                          access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [mock.call(self.cifs_share.cmd_change_access(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_share_access(self):
        self.ssh_hook.append('Command succeeded')

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.deny_share_access(
            mover_name=self.vdm.vdm_name,
            share_name=self.cifs_share.share_name,
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [
            mock.call(self.cifs_share.cmd_change_access(action='revoke'),
                      check_exit_code=True),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_share_access_no_ace(self):
        expt_no_ace = SSHExecutionError(
            stdout=self.cifs_share.output_deny_access_but_no_ace())
        self.ssh_hook.append(ex=expt_no_ace)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.deny_share_access(
            mover_name=self.vdm.vdm_name,
            share_name=self.cifs_share.share_name,
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [
            mock.call(self.cifs_share.cmd_change_access(action='revoke'),
                      check_exit_code=True),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_share_access_but_no_user_found(self):
        expt_no_user = SSHExecutionError(
            stdout=self.cifs_share.output_deny_access_but_no_user_found())
        self.ssh_hook.append(ex=expt_no_user)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.deny_share_access(
            mover_name=self.vdm.vdm_name,
            share_name=self.cifs_share.share_name,
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [
            mock.call(self.cifs_share.cmd_change_access(action='revoke'),
                      check_exit_code=True),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_share_access_with_error(self):
        expt_err = SSHExecutionError(
            self.cifs_share.fake_output)
        self.ssh_hook.append(ex=expt_err)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.deny_share_access,
                          mover_name=self.vdm.vdm_name,
                          share_name=self.cifs_share.share_name,
                          user_name=self.cifs_server.domain_user,
                          domain=self.cifs_server.domain_name,
                          access=constants.CIFS_ACL_FULLCONTROL)

        ssh_calls = [
            mock.call(self.cifs_share.cmd_change_access(action='revoke'),
                      check_exit_code=True),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_operations_with_cifs_share_resource(self):
        self.hook.append(self.vdm.resp_get_succeed())
        self.hook.append(self.cifs_share.resp_task_succeed())
        self.hook.append(self.cifs_share.resp_get_succeed(self.vdm.vdm_id))
        self.hook.append(self.cifs_share.resp_task_succeed())

        xml_connector = self.share_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.ssh_hook.append('Command succeeded')
        self.ssh_hook.append(self.cifs_share.output_allow_access())
        self.ssh_hook.append('Command succeeded')

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        share = self.share_manager.create(
            name=self.cifs_share.share_name,
            server_name=self.cifs_share.cifs_server_name[-14:],
            mover_name=self.vdm.vdm_name,
            is_vdm=True)

        share.disable_share_access()

        share.allow_share_access(
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        share.deny_share_access(
            user_name=self.cifs_server.domain_user,
            domain=self.cifs_server.domain_name,
            access=constants.CIFS_ACL_FULLCONTROL)

        share.delete()

        expected_calls = [
            mock.call(self.vdm.req_get()),
            mock.call(self.cifs_share.req_create(self.vdm.vdm_id)),
            mock.call(self.cifs_share.req_get()),
            mock.call(self.cifs_share.req_delete(self.vdm.vdm_id)),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

        ssh_calls = [
            mock.call(self.cifs_share.cmd_disable_access(),
                      check_exit_code=True),
            mock.call(self.cifs_share.cmd_change_access(),
                      check_exit_code=True),
            mock.call(self.cifs_share.cmd_change_access(action='revoke'),
                      check_exit_code=True)
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)
