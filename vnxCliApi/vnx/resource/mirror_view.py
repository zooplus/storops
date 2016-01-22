# coding=utf-8
from __future__ import unicode_literals

from vnxCliApi.exception import ObjectNotFound
from vnxCliApi.lib.common import check_text
from vnxCliApi.vnx.enums import VNXMirrorViewRecoveryPolicy
from vnxCliApi.vnx.enums import VNXMirrorViewSyncRate
from vnxCliApi.vnx.resource.lun import VNXLun
from vnxCliApi.vnx.resource.resource import VNXResource, VNXCliResourceList

__author__ = 'Cedric Zhuang'


class VNXMirrorViewImage(VNXResource):
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


class VNXMirrorView(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXMirrorView, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_mirror_view(name=self._name)

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
                                        recovery_policy, sync_rate)

    def get_image(self, image_id):
        for image in self.images:
            if image.uid == image_id:
                ret = image
                break
        else:
            raise ObjectNotFound('image {} not found in mirror view {}.'
                                 .format(image_id, self._get_name()))
        return ret

    @staticmethod
    def _get_image_id(image_id):
        return VNXMirrorViewImage.get_id(image_id)

    def remove_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.remove_mirror_view_image(self._get_name(), image_id)

    def fracture_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.mirror_view_fracture_image(self._get_name(), image_id)

    def sync_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.mirror_view_sync_image(self._get_name(), image_id)

    def promote_image(self, image_id):
        image_id = self._get_image_id(image_id)
        self._cli.mirror_view_promote_image(self._get_name(), image_id)


class VNXMirrorViewList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXMirrorView

    def __init__(self, cli=None):
        super(VNXMirrorViewList, self).__init__()
        self._cli = cli

    def _get_raw_resource(self):
        return self._cli.get_mirror_view()
