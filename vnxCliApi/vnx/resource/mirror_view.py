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

from vnxCliApi.exception import VNXObjectNotFound
from vnxCliApi.lib.common import check_text
from vnxCliApi.vnx.enums import VNXMirrorViewRecoveryPolicy
from vnxCliApi.vnx.enums import VNXMirrorViewSyncRate
from vnxCliApi.vnx.resource.lun import VNXLun
from vnxCliApi.vnx.resource.resource import VNXCliResource, VNXCliResourceList

__author__ = 'Cedric Zhuang'


class VNXMirrorViewImage(VNXCliResource):
    @staticmethod
    def get_id(image):
        if isinstance(image, VNXMirrorViewImage):
            image = image.uid
        try:
            image = check_text(image)
        except ValueError:
            raise ValueError('invalid image id supplied: {}'
                             .format(image))
        return image

    @property
    def wwn(self):
        return self.uid


class VNXMirrorViewImageList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXMirrorViewImage


class VNXMirrorView(VNXCliResource):
    def __init__(self, name=None, cli=None):
        super(VNXMirrorView, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_mirror_view(name=self._name, poll=self.poll)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXMirrorViewList(cli)
        else:
            ret = VNXMirrorView(name, cli)
        return ret

    def add_image(self, sp_ip, lun_id,
                  recovery_policy=VNXMirrorViewRecoveryPolicy.AUTO,
                  sync_rate=VNXMirrorViewSyncRate.HIGH):
        lun_id = VNXLun.get_id(lun_id)
        self._cli.add_mirror_view_image(self._get_name(), sp_ip, lun_id,
                                        recovery_policy, sync_rate,
                                        poll=self.poll)

    def get_image(self, image_id):
        for image in self.images:
            if image.uid == image_id:
                ret = image
                break
        else:
            raise VNXObjectNotFound('image {} not found in mirror view {}.'
                                    .format(image_id, self._get_name()))
        return ret

    @staticmethod
    def _get_image_id(image_id):
        return VNXMirrorViewImage.get_id(image_id)

    def remove_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.remove_mirror_view_image(self._get_name(), image_id,
                                           poll=self.poll)

    def fracture_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.mirror_view_fracture_image(self._get_name(), image_id,
                                             poll=self.poll)

    def sync_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.mirror_view_sync_image(self._get_name(), image_id,
                                         poll=self.poll)

    def promote_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.mirror_view_promote_image(self._get_name(), image_id,
                                            poll=self.poll)


class VNXMirrorViewList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXMirrorView

    def __init__(self, cli=None):
        super(VNXMirrorViewList, self).__init__()
        self._cli = cli

    def _get_raw_resource(self):
        return self._cli.get_mirror_view(poll=self.poll)
