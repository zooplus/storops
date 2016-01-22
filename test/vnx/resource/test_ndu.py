# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to

from test.vnx.cli_mock import patch_cli, t_cli
from vnxCliApi.vnx.resource.ndu import VNXNdu

__author__ = 'Cedric Zhuang'


class VNXNduTest(TestCase):
    @patch_cli()
    def test_get_all(self):
        ndu_list = VNXNdu.get(t_cli())
        assert_that(len(ndu_list), equal_to(16))

    @patch_cli()
    def test_get(self):
        ndu = VNXNdu.get(t_cli(), '-VNXSnapshots')
        assert_that(ndu.name, equal_to('-VNXSnapshots'))
        assert_that(ndu.revision, equal_to('-'))
        assert_that(ndu.commit_required, equal_to(False))
        assert_that(ndu.revert_possible, equal_to(False))
        assert_that(ndu.active_state, equal_to(True))
        assert_that(ndu.is_installation_completed, equal_to(True))
        assert_that(ndu.is_this_system_software, equal_to(False))
