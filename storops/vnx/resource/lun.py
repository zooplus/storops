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

from storops.lib.common import check_int
from storops import exception as ex
from storops.vnx.enums import VNXLunType, VNXTieringEnum, VNXProvisionEnum, \
    VNXMigrationRate, raise_if_err, VNXError
from storops.vnx.resource import VNXCliResourceList, VNXCliResource
import storops.vnx.resource.block_pool
from storops.vnx.resource.migration import VNXMigrationSession
import storops.vnx.resource.sg
import storops.vnx.resource.cg
from storops.vnx.resource.snap import VNXSnap, VNXSnapList

__author__ = 'Cedric Zhuang'


class VNXLunList(VNXCliResourceList):
    def __init__(self, cli=None, lun_type=None, lun_ids=None):
        super(VNXLunList, self).__init__(cli)
        self._lun_type = VNXLunType.parse(lun_type)
        self._lun_ids = lun_ids

    def filter(self, lun):
        if self._lun_ids:
            ret = VNXLun.get_id(lun) in self._lun_ids
        else:
            ret = True
        return ret

    @classmethod
    def get_resource_class(cls):
        return VNXLun

    def _get_raw_resource(self):
        return self._cli.get_lun(lun_type=self._lun_type, poll=self.poll)


class VNXLun(VNXCliResource):
    DEFAULT_TIER = VNXTieringEnum.HIGH_AUTO
    DEFAULT_PROVISION = VNXProvisionEnum.THICK

    def __init__(self, lun_id=None, name=None, cli=None):
        super(VNXLun, self).__init__()
        self._cli = cli
        self._lun_id = lun_id
        self._name = name

    def _get_raw_resource(self):
        if self._cli is None:
            raise ValueError('client is not available for this resource.')
        return self._cli.get_lun(name=self._name, lun_id=self._lun_id,
                                 poll=self.poll)

    @property
    def is_snap_mount_point(self):
        return self.primary_lun != 'N/A'

    @staticmethod
    def create(cli,
               pool_id=None,
               pool_name=None,
               lun_id=None,
               lun_name=None,
               size_gb=1,
               provision=None,
               tier=None,
               ignore_thresholds=None):
        cls = storops.vnx.resource.block_pool.VNXPool
        pool = cls(pool_id, pool_name, cli)
        return pool.create_lun(lun_name, size_gb, lun_id, provision,
                               tier, ignore_thresholds)

    def create_mount_point(self, mount_point_id=None, mount_point_name=None):
        lun_id = self.get_id(self)
        self._cli.create_mount_point(primary_lun_id=lun_id,
                                     mount_point_name=mount_point_name,
                                     mount_point_id=mount_point_id,
                                     poll=self.poll)
        return VNXLun(lun_id=mount_point_id,
                      name=mount_point_name,
                      cli=self._cli)

    @property
    def tier(self):
        try:
            tier = VNXTieringEnum.get_tier(
                self.initial_tier,
                self.tiering_policy)
        except AttributeError:
            tier = self.DEFAULT_TIER
        return tier

    @tier.setter
    def tier(self, new_tier):
        out = self._cli.modify_lun(lun_id=self._lun_id,
                                   lun_name=self._name,
                                   new_tier=new_tier,
                                   poll=self.poll)
        msg = 'error change lun tier.'
        raise_if_err(out, ex.VNXModifyLunError, msg)

    @property
    def provision(self):
        ret = self.DEFAULT_PROVISION
        try:
            if self.is_thin_lun:
                ret = VNXProvisionEnum.THIN
            if self.is_compressed:
                ret = VNXProvisionEnum.COMPRESSED
            elif self.is_dedup:
                ret = VNXProvisionEnum.DEDUPED
        except AttributeError:
            pass
        return ret

    @staticmethod
    def get(cli, lun_id=None, name=None, lun_type=None, poll=True):
        if lun_id is None and name is None:
            ret = VNXLunList(cli, lun_type)
        else:
            ret = VNXLun(lun_id, name, cli)
        ret.poll = poll
        return ret

    def create_snap(self, name, allow_rw=None, auto_delete=None):
        out = self._cli.create_snap(self.get_id(self), name, allow_rw,
                                    auto_delete,
                                    poll=self.poll)
        raise_if_err(out, ex.VNXSnapNameExistedError, 'snap name used.',
                     VNXError.SNAP_NAME_EXISTED)
        raise_if_err(out, ex.VNXCreateSnapError,
                     'failed to create snap "{}"'.format(name))
        return VNXSnap(name, self._cli)

    def attach_snap(self, snap):
        snap_name = VNXSnap.get_name(snap)
        out = self._cli.attach_snap(snap_name, lun_id=self.get_id(self),
                                    poll=self.poll)
        if len(out):
            raise ex.VNXAttachSnapError(out)

    def detach_snap(self):
        out = self._cli.detach_snap(lun_id=self.get_id(self), poll=self.poll)
        if len(out):
            raise ex.VNXDetachSnapError(out)

    def get_snap(self, name=None):
        if name is not None:
            ret = VNXSnap.get(self._cli, name)
        else:
            ret = VNXSnapList(self._cli, res=self.get_id(self))
        return ret

    def remove_snap(self, name):
        VNXSnap(name, self._cli).remove()

    def migrate(self, tgt, rate=VNXMigrationRate.HIGH):
        tgt_id = self.get_id(tgt)
        src_id = self.get_id(self)
        out = self._cli.migrate_lun(src_id, tgt_id, rate, poll=self.poll)
        if len(out) > 0:
            raise ex.VNXMigrationError(out)

    def expand(self, new_size, ignore_thresholds=False):
        out = self._cli.expand_pool_lun(new_size, self.get_id(self),
                                        ignore_thresholds=ignore_thresholds,
                                        poll=self.poll)
        raise_if_err(out, ex.VNXLunExpandSizeError, 'target size too small.',
                     VNXError.LUN_EXPAND_ERROR_SIZE)
        raise_if_err(out, ex.VNXLunPreparingError,
                     'LUN is in preparing state.',
                     VNXError.LUN_IS_PREPARING)
        raise_if_err(out, ex.VNXLunExtendError,
                     'failed to expand lun.')

    def cancel_migrate(self):
        src_id = self.get_id(self)
        out = self._cli.cancel_migrate_lun(src_id, poll=self.poll)
        if len(out) > 0:
            raise ex.VNXMigrationError(out)

    def get_migration_session(self):
        return VNXMigrationSession.get(self._cli, self)

    @staticmethod
    def get_id(lun):
        if isinstance(lun, VNXLun):
            if lun._lun_id is not None:
                lun = lun._lun_id
            else:
                lun = lun.lun_id
        try:
            lun = check_int(lun)
        except ValueError:
            raise ValueError('invalid lun number supplied: {}'
                             .format(lun))
        return lun

    @classmethod
    def get_id_list(cls, *lun_list):
        return list(map(cls.get_id, lun_list))

    def detach_from_sg(self, sg=None):
        if sg is None:
            clz = storops.vnx.resource.sg.VNXStorageGroupList
            obj = clz(cli=self._cli)
        else:
            obj = sg
        obj.detach_alu(self)

    def detach_from_cg(self, cg=None):
        if cg is None:
            clz = storops.vnx.resource.cg.VNXConsistencyGroupList
            obj = clz(cli=self._cli)
        else:
            obj = cg
        obj.remove_member(self)

    def remove(self, remove_snapshots=False, force_detach=False,
               detach_from_sg=False, detach_from_cg=False, force=False):
        if force:
            remove_snapshots = True
            force_detach = True
            detach_from_sg = True
            detach_from_cg = True

        if detach_from_sg:
            self.detach_from_sg()

        if detach_from_cg:
            self.detach_from_cg()

        out = self._cli.remove_pool_lun(self._lun_id,
                                        self._name,
                                        remove_snapshots=remove_snapshots,
                                        force_detach=force_detach,
                                        poll=self.poll)

        raise_if_err(out, ex.VNXLunNotFoundError,
                     expected_error=VNXError.GENERAL_NOT_FOUND)
        raise_if_err(out, ex.VNXRemoveLunError, 'failed to remove lun.')

    def rename(self, new_name):
        if new_name is not None and self._name != new_name:
            out = self._cli.modify_lun(lun_id=self._lun_id,
                                       lun_name=self._name,
                                       new_name=new_name,
                                       poll=self.poll)
            raise_if_err(out, ex.VNXModifyLunError,
                         'failed to change lun name.')
            self._name = new_name

    def __setattr__(self, key, value):
        if key == 'name':
            self.rename(value)
            return
        elif key == 'is_compressed':
            if value:
                self.enable_compression()
            else:
                self.disable_compression()
            return
        elif key == 'is_dedup':
            self._update_dedup_state(value)
            return
        super(VNXLun, self).__setattr__(key, value)

    def enable_compression(self, rate=None, ignore_thresholds=None):
        lun_id = self.get_id(self)
        out = self._cli.enable_compression(
            lun_id=lun_id, rate=rate, ignore_thresholds=ignore_thresholds,
            poll=self.poll)
        msg = 'failed to enable compression on {}.'.format(lun_id)
        raise_if_err(out, ex.VNXCompressionAlreadyEnabledError, msg,
                     VNXError.COMPRESSION_ALREADY_ENABLED)
        raise_if_err(out, ex.VNXCompressionError, msg)

    def disable_compression(self, ignore_thresholds=None):
        lun_id = self.get_id(self)
        out = self._cli.disable_compression(lun_id, ignore_thresholds,
                                            poll=self.poll)
        raise_if_err(out, ex.VNXCompressionError,
                     'failed to disable compression on {}.'.format(lun_id))

    def _update_dedup_state(self, tgt_state):
        out = self._cli.modify_lun(lun_id=self._lun_id,
                                   lun_name=self._name,
                                   dedup=tgt_state, poll=self.poll)
        raise_if_err(out, ex.VNXDedupError,
                     'failed to set dedup state to {} for {}.'
                     .format(tgt_state, self.get_id(self)))

    def enable_dedup(self):
        self._update_dedup_state(True)

    def disable_dedup(self):
        self._update_dedup_state(False)

    @property
    def snapshot_mount_points(self):
        smp_ids = self.snapshot_mount_point_ids
        return VNXLunList(cli=self._cli, lun_ids=smp_ids)
