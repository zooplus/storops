# coding=utf-8
# Copyright (c) 2015 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, instance_of
from hamcrest import equal_to

from test.vnx.cli_mock import patch_cli
from test.vnx.cli_mock import t_cli
from vnxCliApi.vnx.enums import VNXMirrorViewRecoveryPolicy, \
    VNXMirrorViewSyncRate, VNXSPEnum
from vnxCliApi.vnx.resource.mirror_view import VNXMirrorView, \
    VNXMirrorViewImage

__author__ = 'Cedric Zhuang'


class VNXMirrorViewTest(TestCase):
    @patch_cli()
    def test_get_all(self):
        mv_list = VNXMirrorView.get(t_cli())
        assert_that(len(mv_list), equal_to(4))

    @patch_cli(output='mirror_not_installed.txt')
    def test_mirror_view_not_installed(self):
        mv_list = VNXMirrorView.get(t_cli())
        assert_that(len(mv_list), equal_to(0))

        mv = VNXMirrorView.get(t_cli(), 'mv_sync_2')
        assert_that(mv.existed, equal_to(False))

    @patch_cli()
    def test_get(self):
        mv = VNXMirrorView.get(t_cli(), 'mv_sync_2')
        assert_that(mv.uid, equal_to(
            '50:06:01:60:88:60:05:FE:04:00:00:00:00:00:00:00'))
        assert_that(mv.name, equal_to('mv_sync_2'))
        assert_that(mv.description, equal_to(''))
        assert_that(mv.logical_unit_numbers, 30)
        assert_that(mv.quiesce_threshold, equal_to(60))
        assert_that(mv.recovery_policy,
                    equal_to(VNXMirrorViewRecoveryPolicy.MANUAL))
        assert_that(len(mv.images), equal_to(2))
        assert_that(mv.images[0], instance_of(VNXMirrorViewImage))
        assert_that(mv.synchronization_rate,
                    equal_to(VNXMirrorViewSyncRate.MEDIUM))
        assert_that(mv.existed, equal_to(True))
        assert_that(mv.state, equal_to('Active'))
        assert_that(mv.image_transitioning, equal_to(False))
        assert_that(mv.image_size, equal_to(2097152))
        assert_that(mv.image_count, equal_to(2))
        assert_that(mv.image_faulted, equal_to(False))
        assert_that(mv.minimum_number_of_images_required, equal_to(0))
        assert_that(mv.write_intent_log_used, equal_to(True))
        assert_that(mv.synchronizing_progress, equal_to(100))
        assert_that(mv.remote_mirror_status, equal_to('Secondary Copy'))
        assert_that(mv.faulted, equal_to(False))
        assert_that(mv.transitioning, equal_to(False))


class VNXMirrorViewImageTest(TestCase):
    @patch_cli()
    def test_properties(self):
        mv = VNXMirrorView.get(t_cli(), 'mv_sync_2')
        image = mv.get_image('50:06:01:60:88:60:05:FE')
        assert_that(image.uid, equal_to('50:06:01:60:88:60:05:FE'))
        assert_that(image.existed, equal_to(True))
        assert_that(image.is_image_primary, equal_to(True))
        assert_that(image.logical_unit_uid, equal_to(
            '60:06:01:60:41:C4:3D:00:6E:1C:50:9D:05:95:E5:11'))
        assert_that(image.image_condition, equal_to('Primary Image'))
        assert_that(image.preferred_sp, equal_to(VNXSPEnum.SP_A))
