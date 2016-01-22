# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to, contains_string, is_not

from test.vnx.cli_mock import t_cli, patch_cli
from vnxCliApi.vnx.resource.domain_member import VNXDomainMemberList

__author__ = 'Cedric Zhuang'


class VNXDomainMemberListTest(TestCase):
    def setUp(self):
        self.dml = VNXDomainMemberList(t_cli())

    @patch_cli()
    def test_iterable(self):
        count = 0
        for _ in self.dml:
            count += 1
        assert_that(count, equal_to(3))

    @patch_cli()
    def test_properties(self):
        str_value = str(self.dml)
        assert_that(str_value, contains_string('VNXDomainMember'))
        assert_that(str_value, contains_string('VNXDomainMemberList'))
        assert_that(str_value, is_not(contains_string('::')))

    @patch_cli()
    def test_sp(self):
        spa = self.dml.spa
        assert_that(spa.ip, equal_to('10.244.211.30'))
        assert_that(spa.is_master, equal_to(True))
        spb = self.dml.spb
        assert_that(spb.ip, equal_to('10.244.211.31'))
        assert_that(spb.is_master, equal_to(False))
        cs = self.dml.control_station
        assert_that(cs.ip, equal_to('10.244.211.32'))
