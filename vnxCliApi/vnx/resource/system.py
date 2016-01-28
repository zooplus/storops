# coding=utf-8
from __future__ import unicode_literals

from vnxCliApi.lib.common import daemon, cache
from vnxCliApi.vnx.cli import CliClient
from vnxCliApi.vnx.resource.block_pool import VNXPool, VNXPoolFeature
from vnxCliApi.vnx.resource.cg import VNXConsistencyGroup
from vnxCliApi.vnx.resource.disk import VNXDisk
from vnxCliApi.vnx.resource.vnx_domain import VNXDomainMemberList, \
    VNXNetworkAdmin, VNXDomainNodeList
from vnxCliApi.vnx.resource.lun import VNXLun
from vnxCliApi.vnx.resource.migration import VNXMigrationSession
from vnxCliApi.vnx.resource.ndu import VNXNdu
from vnxCliApi.vnx.resource.port import VNXConnectionPort
from vnxCliApi.vnx.resource.resource import VNXCliResource
from vnxCliApi.vnx.resource.rg import VNXRaidGroup
from vnxCliApi.vnx.resource.sg import VNXStorageGroup
from vnxCliApi.vnx.resource.snap import VNXSnap

__author__ = 'Cedric Zhuang'


class VNXSystem(VNXCliResource):
    """ The system class for VNX

    This class act as the entry point for VNX system.
    Various VNX resources could be retrieved with methods/properties
    of this class.
    """

    def __init__(self, ip=None,
                 username=None, password=None, scope=0, sec_file=None,
                 timeout=None,
                 heartbeat_interval=None,
                 naviseccli=None):
        """ initialize a `VNXSystem` instance

        The `VNXSystem` instance act as a entry point for all
        VNX resources.

        :param ip: ip of one block sp
        :param username: username for block system
        :param password: password for the specified block user
        :param scope: scope of the specified block user
        :param sec_file: security file used by naviseccli
        :param timeout: naviseccli command timeout
        :param heartbeat_interval: heartbeat interval used to check the
        alive of sp.  Set to 0 if heart beat is not required.
        :param naviseccli: binary location of naviseccli in your host.
        :return: vnx system instance
        """
        super(VNXSystem, self).__init__()
        self._cli = CliClient(ip,
                              username, password, scope,
                              sec_file,
                              timeout,
                              heartbeat_interval=heartbeat_interval,
                              naviseccli=naviseccli)
        daemon(self._update_nodes_ip)

    def set_naviseccli(self, cli_binary):
        self._cli.set_binary(cli_binary)

    def set_block_credential(self,
                             username=None, password=None, scope=None,
                             sec_file=None):
        self._cli.set_credential(username, password, scope, sec_file)

    def _update_nodes_ip(self):
        self._cli.set_ip(self.spa_ip, self.spb_ip, self.control_station_ip)

    @property
    def heartbeat(self):
        return self._cli.heartbeat

    @property
    @cache()
    def spa_ip(self):
        return VNXNetworkAdmin.get_spa_ip(self._cli)

    @property
    @cache()
    def spb_ip(self):
        return VNXNetworkAdmin.get_spb_ip(self._cli)

    @property
    @cache()
    def control_station_ip(self):
        return VNXDomainNodeList.get_cs_ip(self.serial, self._cli)

    @property
    def domain(self):
        return VNXDomainMemberList(self._cli)

    def _get_raw_resource(self):
        return self._cli.get_agent(poll=self.poll)

    def get_pool_feature(self):
        return VNXPoolFeature(self._cli)

    def get_pool(self, pool_id=None, name=None):
        return VNXPool.get(pool_id=pool_id, name=name, cli=self._cli)

    def get_lun(self, lun_id=None, name=None, lun_type=None):
        return VNXLun.get(self._cli, lun_id=lun_id, name=name,
                          lun_type=lun_type)

    def get_cg(self, name=None):
        return VNXConsistencyGroup.get(self._cli, name)

    def get_sg(self, name=None):
        return VNXStorageGroup.get(self._cli, name)

    def get_snap(self, name=None):
        return VNXSnap.get(self._cli, name)

    def get_migration_session(self, src_lun=None):
        return VNXMigrationSession.get(self._cli, src_lun)

    def get_ndu(self, name=None):
        return VNXNdu.get(self._cli, name)

    def get_port(self, sp=None, port_id=None, vport_id=None):
        return VNXConnectionPort.get(self._cli, sp, port_id, vport_id)

    def remove_snap(self, name):
        self._remove_resource(VNXSnap(name, self._cli))

    def create_sg(self, name):
        return VNXStorageGroup.create(name, self._cli)

    def remove_sg(self, name):
        self._remove_resource(VNXStorageGroup(name, self._cli))

    def create_cg(self, name, members=None):
        return VNXConsistencyGroup.create(self._cli, name=name,
                                          members=members)

    def remove_cg(self, name):
        self._remove_resource(VNXConsistencyGroup(name, self._cli))

    def get_disk(self, disk_index=None):
        return VNXDisk.get(self._cli, disk_index)

    def remove_disk(self, disk_index):
        self._remove_resource(VNXDisk(disk_index, self._cli))

    def install_disk(self, disk_index):
        disk = VNXDisk(disk_index, self._cli)
        disk.install()

    def get_rg(self, rg_id=None):
        return VNXRaidGroup.get(self._cli, rg_id)

    def create_rg(self, rg_id, disks, raid_type=None):
        return VNXRaidGroup.create(self._cli, rg_id, disks, raid_type)

    def remove_rg(self, rg_id):
        self._remove_resource(VNXRaidGroup(rg_id, self._cli))

    def create_pool(self, name, disks, raid_type=None):
        return VNXPool.create(self._cli, name, disks, raid_type)

    def _remove_resource(self, resource):
        resource.poll = self.poll
        resource.remove()

    def remove_pool(self, name=None, pool_id=None):
        self._remove_resource(VNXPool(pool_id, name, self._cli))

    def stop_heart_beat(self):
        self._cli.heartbeat.stop()

    def __del__(self):
        del self._cli
