# coding=utf-8
from __future__ import unicode_literals

import logging

from lxml import builder

from vnxCliApi.connection import connector
from vnxCliApi.exception import VNXBackendError
from vnxCliApi.lib import common
from vnxCliApi.lib import xmlapi
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import filesystem, nas_pool, mover, vdm, \
    mover_interface, dns_domain, mount_point, filesystem_snapshot, \
    cifs_server, cifs_share, nfs_share

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


@common.decorate_all_methods(common.log_enter_exit)
class StorageManager(object):
    def __init__(self, host, username, password):
        self.xml = {
            'connector': connector.XMLAPIConnector(host, username, password),
            'builder': builder.ElementMaker(
                nsmap={None: constants.XML_NAMESPACE}),
            'parser': xmlapi.XMLAPIParser(),
        }

        self.ssh = {
            'connector': connector.SSHConnector(host, username, password),
        }

        self.filesystems = filesystem.FileSystemManager(self)
        self.nas_pools = nas_pool.PoolManager(self)
        self.movers = mover.MoverManager(self)
        self.movers_ref = mover.MoverRefManager(self)
        self.vdms = vdm.VDMManager(self)
        self.mover_interfaces = mover_interface.MoverInterfaceManager(self)
        self.dns_domains = dns_domain.DNSDomainManager(self)
        self.mountpoints = mount_point.MountPointManager(self)
        self.fs_snapshots = filesystem_snapshot.SnapshotManager(self)
        self.cifs_servers = cifs_server.CIFSServerManager(self)
        self.cifs_shares = cifs_share.CIFSShareManager(self)
        self.nfs_shares = nfs_share.NFSShareManager(self)

        self.manager_map = {
            'pool': self.nas_pools,
            'filesystem': self.filesystems,
            'mover_ref': self.movers_ref,
            'mover': self.movers,
            'vdm': self.vdms,
            'mover_interface': self.mover_interfaces,
            'dns_domain': self.dns_domains,
            'mount': self.mountpoints,
            'snapshot': self.fs_snapshots,
            'cifs_server': self.cifs_servers,
            'cifs_share': self.cifs_shares,
            'nfs_share': self.nfs_shares,
        }

    def get_object_manager(self, manager_type):
        if manager_type in self.manager_map:
            return self.manager_map[manager_type]
        else:
            message = "Invalid storage object type {}.".format(manager_type)
            log.error(message)
            raise VNXBackendError(err=message)
