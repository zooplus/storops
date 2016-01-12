# coding=utf-8
from __future__ import unicode_literals

import unittest

import mock

from test.vnx.resource.fakes import mock_ssh_connector, patch_retry
from test.vnx.resource.fakes import mock_xml_api
from vnxCliApi.vnx.resource import manager

from test import utils
from test.vnx.resource import fakes
from vnxCliApi.exception import VNXBackendError
from vnxCliApi.vnx.resource import dns_domain

__author__ = 'Jay Xu'


class DNSDomainTestCase(unittest.TestCase):
    @mock_xml_api
    @mock_ssh_connector
    def setUp(self):
        super(self.__class__, self).setUp()
        self.hook = utils.RequestSideEffect()

        host = fakes.FakeData.emc_nas_server
        username = fakes.FakeData.emc_nas_login
        password = fakes.FakeData.emc_nas_password
        storage_manager = manager.StorageManager(host, username, password)
        self.dns_manager = dns_domain.DNSDomainManager(storage_manager)

        self.mover = fakes.MoverTestData()
        self.dns = fakes.DNSDomainTestData()

    def test_create_dns_domain(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_task_succeed())

        xml_connector = self.dns_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.dns_manager.create(mover_name=self.mover.mover_name,
                                name=self.dns.domain_name,
                                servers=self.dns.dns_ip_address)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_create_dns_domain_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_task_succeed())

        xml_connector = self.dns_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.dns_manager.create(mover_name=self.mover.mover_name,
                                name=self.dns.domain_name,
                                servers=self.dns.dns_ip_address)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_create()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_create_dns_domain_with_error(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_task_error())

        xml_connector = self.dns_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.assertRaises(VNXBackendError,
                          self.dns_manager.create,
                          mover_name=self.mover.mover_name,
                          name=self.mover.domain_name,
                          servers=self.dns.dns_ip_address)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_create()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_delete_dns_domain(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_task_succeed())
        self.hook.append(self.dns.resp_task_error())

        xml_connector = self.dns_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.dns_manager.delete(mover_name=self.mover.mover_name,
                                name=self.mover.domain_name)

        self.dns_manager.delete(mover_name=self.mover.mover_name,
                                name=self.mover.domain_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_delete()),
            mock.call(self.dns.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    @patch_retry
    def test_delete_dns_domain_invalid_mover_id(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_invalid_mover_id())
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_task_succeed())

        xml_connector = self.dns_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        self.dns_manager.delete(mover_name=self.mover.mover_name,
                                name=self.mover.domain_name)

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_delete()),
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)

    def test_operations_with_dns_resource(self):
        self.hook.append(self.mover.resp_get_ref_succeed())
        self.hook.append(self.dns.resp_task_succeed())
        self.hook.append(self.dns.resp_task_succeed())

        xml_connector = self.dns_manager.xml_connector
        xml_connector.post = utils.EMCMock(side_effect=self.hook)

        dns = self.dns_manager.create(
            mover_name=self.mover.mover_name,
            name=self.dns.domain_name,
            servers=self.dns.dns_ip_address)

        dns.delete()

        expected_calls = [
            mock.call(self.mover.req_get_ref()),
            mock.call(self.dns.req_create()),
            mock.call(self.dns.req_delete()),
        ]
        xml_connector.post.assert_has_calls(expected_calls)
