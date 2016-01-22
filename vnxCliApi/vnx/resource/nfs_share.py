# coding=utf-8
from __future__ import unicode_literals

import logging
import re

from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import ObjectNotFound
from vnxCliApi.exception import VNXBackendError
from vnxCliApi.lib.common import synchronized
from vnxCliApi.vnx import constants
from vnxCliApi.vnx.resource import file_resource

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


class VNXNfsShare(file_resource.Resource):
    def delete(self):
        self.manager.delete(self.name, self.mover_name)

    def allow_share_access(self, host_ip, access=constants.ACCESS_LEVEL_RW):
        self.manager.allow_share_access(
            self.name, host_ip, self.mover_name, access)

    def deny_share_access(self, host_ip):
        self.manager.deny_share_access(self.name, host_ip, self.mover_name, )


class NFSShareManager(file_resource.ResourceManager):
    """Manage :class:`Share` resources."""
    resource_class = VNXNfsShare

    def __init__(self, manager):
        super(NFSShareManager, self).__init__(manager)
        self.nfs_share_map = dict()

    def create(self, name, mover_name):
        share_path = '/' + name
        create_nfs_share_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_export', mover_name,
            '-option', 'access=-0.0.0.0/0.0.0.0',
            share_path,
        ]

        try:
            self._execute_cmd(create_nfs_share_cmd, check_exit_code=True)
        except SSHExecutionError as expt:
            message = ('Failed to create NFS share %(name)s on mover '
                       '%(mover_name)s. Reason: %(err)s.' %
                       {'name': name, 'mover_name': mover_name, 'err': expt})
            log.error(message)
            raise VNXBackendError(err=message)

        share = {
            'name': name,
            'path': share_path,
            'mover_name': mover_name,
        }

        self.nfs_share_map[name] = self.resource_class(self, share)

        return self.nfs_share_map[name]

    def delete(self, name, mover_name, check_exit_code=False):
        path = '/' + name

        try:
            self.get(name, mover_name, check_exit_code=True)
        except ObjectNotFound:
            log.warn("NFS share %s not found. Skip the deletion.", path)
            return

        delete_nfs_share_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_export', mover_name,
            '-unexport',
            '-perm',
            path,
        ]

        try:
            self._execute_cmd(delete_nfs_share_cmd,
                              check_exit_code=check_exit_code)
        except SSHExecutionError as expt:
            message = ('Failed to delete NFS share %(name)s on '
                       '%(mover_name)s. Reason: %(err)s.' %
                       {'name': name, 'mover_name': mover_name, 'err': expt})
            log.error(message)
            raise VNXBackendError(err=message)

        if name in self.nfs_share_map:
            self.nfs_share_map.pop(name)

    def get_resource(self, resource):
        return self.get(resource.name, resource.mover_name)

    def get(self, name, mover_name, check_exit_code=False):
        if not self._cache_missed(name, self.nfs_share_map):
            return self.nfs_share_map[name]

        path = '/' + name

        nfs_share = {
            'name': name,
            "mover_name": mover_name,
            "path": path,
            'AccessHosts': [],
            'RwHosts': [],
            'RoHosts': [],
            'RootHosts': [],
        }

        nfs_query_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_export', mover_name,
            '-P', 'nfs',
            '-list', path,
        ]

        try:
            out, err = self._execute_cmd(nfs_query_cmd,
                                         check_exit_code=check_exit_code)
        except SSHExecutionError as expt:
            message = ('Failed to get NFS share %(name)s on '
                       '%(mover_name)s. Reason: %(err)s.' %
                       {'name': name,
                        'mover_name': mover_name,
                        'err': expt})
            log.error(message)

            dup_msg = (r'%(mover_name)s : No such file or directory' %
                       {'mover_name': mover_name})
            if re.search(dup_msg, expt.stdout):
                raise ObjectNotFound(err=message)
            else:
                raise VNXBackendError(err=message)

        re_exports = '%s\s*:\s*\nexport\s*(.*)\n' % mover_name
        m = re.search(re_exports, out)
        if m is not None:
            export = m.group(1)
            fields = export.split(" ")
            for field in fields:
                field = field.strip()
                if field.startswith('rw='):
                    nfs_share['RwHosts'] = field[3:].split(":")
                elif field.startswith('access='):
                    nfs_share['AccessHosts'] = field[7:].split(":")
                elif field.startswith('root='):
                    nfs_share['RootHosts'] = field[5:].split(":")
                elif field.startswith('ro='):
                    nfs_share['RoHosts'] = field[3:].split(":")

            if name not in self.nfs_share_map:
                self.nfs_share_map[name] = self.resource_class(
                    self, nfs_share, loaded=True)
            else:
                self.nfs_share_map[name].update(nfs_share)

            return self.nfs_share_map[name]

        return None

    def allow_share_access(self, share_name, host_ip, mover_name,
                           access_level=constants.ACCESS_LEVEL_RW):
        @synchronized('emc-shareaccess-' + share_name)
        def do_allow_access(share_name, host_ip, mover_name, access_level):
            share = self.get(share_name, mover_name, check_exit_code=True)

            changed = False
            if access_level == constants.ACCESS_LEVEL_RW:
                if host_ip not in share.rw_hosts:
                    share.rw_hosts.append(host_ip)
                    changed = True
                if host_ip in share.ro_hosts:
                    share.ro_hosts.remove(host_ip)
                    changed = True
            if access_level == constants.ACCESS_LEVEL_RO:
                if host_ip not in share.ro_hosts:
                    share.ro_hosts.append(host_ip)
                    changed = True
                if host_ip in share.rw_hosts:
                    share.rw_hosts.remove(host_ip)
                    changed = True

            if host_ip not in share.root_hosts:
                share.root_hosts.append(host_ip)
                changed = True
            if host_ip not in share.access_hosts:
                share.access_hosts.append(host_ip)
                changed = True

            if not changed:
                log.debug("%(host)s is already in access list of share "
                          "%(name)s.", {'host': host_ip, 'name': share_name})
            else:
                path = '/' + share_name
                self._set_share_access(path,
                                       mover_name,
                                       share.rw_hosts,
                                       share.ro_hosts,
                                       share.root_hosts,
                                       share.access_hosts)

                # Update self.share_map
                share.update()

        do_allow_access(share_name, host_ip, mover_name, access_level)

    def deny_share_access(self, share_name, host_ip, mover_name):

        @synchronized('emc-shareaccess-' + share_name)
        def do_deny_access(share_name, host_ip, mover_name):
            share = self.get(share_name, mover_name)

            changed = False
            if host_ip in share.rw_hosts:
                share.rw_hosts.remove(host_ip)
                changed = True
            if host_ip in share.root_hosts:
                share.root_hosts.remove(host_ip)
                changed = True
            if host_ip in share.access_hosts:
                share.access_hosts.remove(host_ip)
                changed = True
            if host_ip in share.ro_hosts:
                share.ro_hosts.remove(host_ip)
                changed = True
            if not changed:
                log.debug("%(host)s is already in access list of share "
                          "%(name)s.", {'host': host_ip, 'name': share_name})
            else:
                path = '/' + share_name
                self._set_share_access(path,
                                       mover_name,
                                       share.rw_hosts,
                                       share.ro_hosts,
                                       share.root_hosts,
                                       share.access_hosts)

                # Update self.nfs_share_map
                share.update()

        do_deny_access(share_name, host_ip, mover_name)

    def _set_share_access(self, path, mover_name, rw_hosts, ro_hosts,
                          root_hosts, access_hosts):

        access_str = ('access=%(access)s'
                      % {'access': ':'.join(access_hosts)})
        if root_hosts:
            access_str += (',root=%(root)s' % {'root': ':'.join(root_hosts)})
        if rw_hosts:
            access_str += ',rw=%(rw)s' % {'rw': ':'.join(rw_hosts)}
        if ro_hosts:
            access_str += ',ro=%(ro)s' % {'ro': ':'.join(ro_hosts)}
        set_nfs_share_access_cmd = [
            'env', 'NAS_DB=/nas', '/nas/bin/server_export', mover_name,
            '-ignore',
            '-option', access_str,
            path,
        ]

        try:
            self._execute_cmd(set_nfs_share_access_cmd, check_exit_code=True)
        except SSHExecutionError as expt:
            message = ('Failed to set NFS share %(name)s access on '
                       '%(mover_name)s. Reason: %(err)s.' %
                       {'name': path[1:],
                        'mover_name': mover_name,
                        'err': expt})
            log.error(message)
            raise VNXBackendError(err=message)
