# coding=utf-8
from __future__ import unicode_literals

import copy
import unittest

import mock

from test import utils
from test.vnx.resource import fakes
from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXBackendError, ObjectNotFound
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import nas_client
from vnxCliApi.vnx.resource import nfs_share

__author__ = 'Jay Xu'


class NFSShareTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.ssh_hook = utils.SSHSideEffect()
        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = nas_client.VNXNasClient(host, username, password)
        self.share_manager = nfs_share.NFSShareManager(storage_manager)

        self.vdm = fakes.VDMTestData()
        self.nfs_share = fakes.NFSShareTestData()

    def test_create_nfs_share(self):
        self.ssh_hook.append(self.nfs_share.output_create())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.create(name=self.nfs_share.share_name,
                                  mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.nfs_share.cmd_create(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_create_nfs_share_with_error(self):
        expt_err = SSHExecutionError(
            stdout=self.nfs_share.fake_output)
        self.ssh_hook.append(ex=expt_err)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.create,
                          name=self.nfs_share.share_name,
                          mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.nfs_share.cmd_create(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_delete_nfs_share(self):
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_delete_succeed())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.delete(name=self.nfs_share.share_name,
                                  mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_delete(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_delete_nfs_share_not_found(self):
        expt_not_found = SSHExecutionError(
            stdout=self.nfs_share.output_get_but_not_found())
        self.ssh_hook.append(ex=expt_not_found)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.delete(name=self.nfs_share.share_name,
                                  mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.nfs_share.cmd_get(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    @patch_retry
    def test_delete_nfs_share_locked(self):
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        expt_locked = SSHExecutionError(
            stdout=self.nfs_share.output_delete_but_locked())
        self.ssh_hook.append(ex=expt_locked)
        self.ssh_hook.append(self.nfs_share.output_delete_succeed())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.delete(name=self.nfs_share.share_name,
                                  mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_delete(), check_exit_code=False),
            mock.call(self.nfs_share.cmd_delete(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_delete_nfs_share_with_error(self):
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        expt_err = SSHExecutionError(
            stdout=self.nfs_share.fake_output)
        self.ssh_hook.append(ex=expt_err)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.delete,
                          name=self.nfs_share.share_name,
                          mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_delete(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_get_nfs_share(self):
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.share_manager.get(name=self.nfs_share.share_name,
                               mover_name=self.vdm.vdm_name,
                               check_exit_code=True)

        # Get NFS share from cache
        self.share_manager.get(name=self.nfs_share.share_name,
                               mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.nfs_share.cmd_get(),
                               check_exit_code=True)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_get_nfs_share_not_found(self):
        expt_not_found = SSHExecutionError(
            stdout=self.nfs_share.output_get_but_not_found())
        self.ssh_hook.append(ex=expt_not_found)
        self.ssh_hook.append(self.nfs_share.output_get_but_not_found())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(ObjectNotFound,
                          self.share_manager.get,
                          name=self.nfs_share.share_name,
                          mover_name=self.vdm.vdm_name,
                          check_exit_code=True)

        self.share_manager.get(name=self.nfs_share.share_name,
                               mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_get(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_get_nfs_share_with_error(self):
        expt_err = SSHExecutionError(
            stdout=self.nfs_share.fake_output)
        self.ssh_hook.append(ex=expt_err)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = mock.Mock(side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.get,
                          name=self.nfs_share.share_name,
                          mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.nfs_share.cmd_get(),
                               check_exit_code=False)]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_allow_share_access(self):
        rw_hosts = copy.deepcopy(self.nfs_share.rw_hosts)
        rw_hosts.append(self.nfs_share.nfs_host_ip)

        ro_hosts = copy.deepcopy(self.nfs_share.ro_hosts)
        ro_hosts.append(self.nfs_share.nfs_host_ip)

        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts, ro_hosts=ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts))

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        self.share_manager.allow_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name,
            access_level=constants.ACCESS_LEVEL_RW)

        self.share_manager.allow_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name,
            access_level=constants.ACCESS_LEVEL_RO)

        self.share_manager.allow_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name,
            access_level=constants.ACCESS_LEVEL_RW)

        self.share_manager.allow_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name,
            access_level=constants.ACCESS_LEVEL_RW)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get()),
            mock.call(self.nfs_share.cmd_set_access(
                rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts)),
            mock.call(self.nfs_share.cmd_get()),
            mock.call(self.nfs_share.cmd_set_access(
                rw_hosts=self.nfs_share.rw_hosts, ro_hosts=ro_hosts)),
            mock.call(self.nfs_share.cmd_get()),
            mock.call(self.nfs_share.cmd_set_access(
                rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts)),
            mock.call(self.nfs_share.cmd_get()),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_allow_share_access_not_found(self):
        expt_not_found = SSHExecutionError(
            stdout=self.nfs_share.output_get_but_not_found())
        self.ssh_hook.append(ex=expt_not_found)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        self.assertRaises(ObjectNotFound,
                          self.share_manager.allow_share_access,
                          share_name=self.nfs_share.share_name,
                          host_ip=self.nfs_share.nfs_host_ip,
                          mover_name=self.vdm.vdm_name,
                          access_level=constants.ACCESS_LEVEL_RW)

        ssh_calls = [mock.call(self.nfs_share.cmd_get())]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_rw_share_access(self):
        rw_hosts = copy.deepcopy(self.nfs_share.rw_hosts)
        rw_hosts.append(self.nfs_share.nfs_host_ip)

        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        self.share_manager.deny_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get()),
            mock.call(self.nfs_share.cmd_set_access(self.nfs_share.rw_hosts,
                                                    self.nfs_share.ro_hosts)),
            mock.call(self.nfs_share.cmd_get()),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_ro_share_access(self):
        ro_hosts = copy.deepcopy(self.nfs_share.ro_hosts)
        ro_hosts.append(self.nfs_share.nfs_host_ip)

        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts, ro_hosts=ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())

        ro_hosts.remove(self.nfs_share.nfs_host_ip)
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        self.share_manager.deny_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name)

        self.share_manager.deny_share_access(
            share_name=self.nfs_share.share_name,
            host_ip=self.nfs_share.nfs_host_ip,
            mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get()),
            mock.call(self.nfs_share.cmd_set_access(self.nfs_share.rw_hosts,
                                                    self.nfs_share.ro_hosts)),
            mock.call(self.nfs_share.cmd_get()),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_share_not_found(self):
        expt_not_found = SSHExecutionError(
            stdout=self.nfs_share.output_get_but_not_found())
        self.ssh_hook.append(ex=expt_not_found)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        self.assertRaises(ObjectNotFound,
                          self.share_manager.deny_share_access,
                          share_name=self.nfs_share.share_name,
                          host_ip=self.nfs_share.nfs_host_ip,
                          mover_name=self.vdm.vdm_name)

        ssh_calls = [mock.call(self.nfs_share.cmd_get())]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_rw_share_with_error(self):
        rw_hosts = copy.deepcopy(self.nfs_share.rw_hosts)
        rw_hosts.append(self.nfs_share.nfs_host_ip)

        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts))
        expt_not_found = SSHExecutionError(
            stdout=self.nfs_share.output_get_but_not_found())
        self.ssh_hook.append(ex=expt_not_found)

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        self.assertRaises(VNXBackendError,
                          self.share_manager.deny_share_access,
                          share_name=self.nfs_share.share_name,
                          host_ip=self.nfs_share.nfs_host_ip,
                          mover_name=self.vdm.vdm_name)

        ssh_calls = [
            mock.call(self.nfs_share.cmd_get()),
            mock.call(self.nfs_share.cmd_set_access(self.nfs_share.rw_hosts,
                                                    self.nfs_share.ro_hosts)),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_allow_access_with_nfs_share_resource(self):
        rw_hosts = copy.deepcopy(self.nfs_share.rw_hosts)
        rw_hosts.append(self.nfs_share.nfs_host_ip)

        ro_hosts = copy.deepcopy(self.nfs_share.ro_hosts)
        ro_hosts.append(self.nfs_share.nfs_host_ip)

        self.ssh_hook.append(self.nfs_share.output_create())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_delete_succeed())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        share = self.share_manager.create(name=self.nfs_share.share_name,
                                          mover_name=self.vdm.vdm_name)

        share.allow_share_access(host_ip=self.nfs_share.nfs_host_ip)

        share.delete()

        ssh_calls = [
            mock.call(self.nfs_share.cmd_create(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_get(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_set_access(
                rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts),
                check_exit_code=True),
            mock.call(self.nfs_share.cmd_get(), check_exit_code=False),
            mock.call(self.nfs_share.cmd_delete(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)

    def test_deny_access_with_nfs_share_resource(self):
        rw_hosts = copy.deepcopy(self.nfs_share.rw_hosts)
        rw_hosts.append(self.nfs_share.nfs_host_ip)

        self.ssh_hook.append(self.nfs_share.output_create())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=rw_hosts, ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_set_access_success())
        self.ssh_hook.append(self.nfs_share.output_get_succeed(
            rw_hosts=self.nfs_share.rw_hosts,
            ro_hosts=self.nfs_share.ro_hosts))
        self.ssh_hook.append(self.nfs_share.output_delete_succeed())

        ssh_connector = self.share_manager.ssh_connector
        ssh_connector.execute = utils.EMCNFSShareMock(
            side_effect=self.ssh_hook)

        share = self.share_manager.create(name=self.nfs_share.share_name,
                                          mover_name=self.vdm.vdm_name)

        share.deny_share_access(host_ip=self.nfs_share.nfs_host_ip)

        share.delete()

        ssh_calls = [
            mock.call(self.nfs_share.cmd_create(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_get(), check_exit_code=True),
            mock.call(self.nfs_share.cmd_set_access(
                self.nfs_share.rw_hosts, self.nfs_share.ro_hosts),
                check_exit_code=True),
            mock.call(self.nfs_share.cmd_get(), check_exit_code=False),
            mock.call(self.nfs_share.cmd_delete(), check_exit_code=False),
        ]
        ssh_connector.execute.assert_has_calls(ssh_calls)
