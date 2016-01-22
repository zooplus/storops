# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to, raises

from test.vnx.cli_mock import patch_cli, t_cli
from test.vnx.resource.verifiers import verify_raid0
from vnxCliApi.exception import VNXCreateRaidGroupError, \
    VNXRemoveRaidGroupError
from vnxCliApi.vnx.resource.rg import VNXRaidGroup

__author__ = 'Cedric Zhuang'


class VNXRaidGroupTest(TestCase):
    @patch_cli()
    def test_get_rg(self):
        rg = VNXRaidGroup.get(t_cli(), 0)
        verify_raid0(rg)

    @patch_cli()
    def test_get_rg_list(self):
        rgs = VNXRaidGroup.get(t_cli())
        assert_that(len(rgs), equal_to(7))
        for rg in rgs:
            if rg.raid_group_id == 0:
                verify_raid0(rg)
                break
        else:
            self.fail('RAID group 0 not found.')

    @patch_cli()
    def test_create_rg(self):
        def f():
            VNXRaidGroup.create(t_cli(), 11, ['1_0_0', '1_0_1'])

        assert_that(f, raises(VNXCreateRaidGroupError, 'not supported'))

    @patch_cli()
    def test_create_rg_invalid_raid_type(self):
        def f():
            VNXRaidGroup.create(t_cli(), 11, ['1_0_0', '1_0_1'], 'r12')

        assert_that(f, raises(ValueError, 'valid value'))

    @patch_cli()
    def test_remove_rg(self):
        def f():
            VNXRaidGroup(11, t_cli()).remove()

        assert_that(f, raises(VNXRemoveRaidGroupError, 'Not Found'))
