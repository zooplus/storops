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

from lxml import builder

from storops.lib import converter

__author__ = 'Cedric Zhuang'


class NasXmlBuilder(builder.ElementMaker):
    namespace = 'http://www.emc.com/schemas/celerra/xml_api'
    default_task_timeout = 5 * 60

    def __init__(self, type_map=None, namespace=None, ns_map=None,
                 makeelement=None):
        if ns_map is None:
            ns_map = {None: self.namespace}
        super(NasXmlBuilder, self).__init__(type_map, namespace, ns_map,
                                            makeelement)

    def query_package(self, body):
        return self.RequestPacket(self.Request(self.Query(body)))

    def task_package(self, body):
        return self.RequestPacket(self.Request(self.StartTask(
            body, timeout=str(self.default_task_timeout))))

    def get_filesystem(self, name=None, fs_id=None):
        param = [self.AspectSelection(
            self._props(['fileSystems',
                         'fileSystemCapacityInfos']))]

        if name is not None:
            param.append(self.Alias(name=name))
        elif fs_id is not None:
            param.append(self.FileSystem(fileSystem=str(fs_id)))

        body = self.FileSystemQueryParams(*param)
        return self.query_package(body)

    def create_filesystem(self, name, size, pool_id,
                          mover_id, is_vdm=False):
        mover = self._get_mover_id_node(mover_id, is_vdm)

        body = self.NewFileSystem(
            mover,
            self.StoragePool(
                pool=str(pool_id),
                size=str(size),
                mayContainSlices='true'),
            name=name)
        return self.task_package(body)

    def extend_filesystem(self, fs_id, delta_size, pool_id=None):
        body = self.ExtendFileSystem(
            self.StoragePool(pool=str(pool_id), size=str(delta_size)),
            fileSystem=str(fs_id))
        return self.task_package(body)

    def _get_mover_id_node(self, mover_id, is_vdm):
        if not is_vdm:
            ret = self.Mover(mover=str(mover_id))
        else:
            ret = self.Vdm(vdm=str(mover_id))
        return ret

    def delete_filesystem(self, fs_id):
        body = self.DeleteFileSystem(fileSystem=str(fs_id))
        return self.task_package(body)

    def get_nas_pool(self):
        return self.query_package(self.StoragePoolQueryParams())

    @staticmethod
    def _props(props):
        return {name: 'true' for name in props}

    @classmethod
    def _get_mover_props(cls, full=True):
        prop_names = ['movers']
        if full:
            prop_names += ['moverDeduplicationSettings',
                           'moverDnsDomains',
                           'moverInterfaces',
                           'moverNetworkDevices',
                           'moverNisDomains',
                           'moverRoutes',
                           'moverStatuses']
        return cls._props(prop_names)

    def get_mover(self, mover_id=None, full=True):
        params = self.AspectSelection(**self._get_mover_props(full))
        kwargs = {}
        if mover_id is not None:
            kwargs['mover'] = str(mover_id)
        body = self.MoverQueryParams(params, **kwargs)
        return self.query_package(body)

    def get_fs_snap(self, name=None, snap_id=None):
        if snap_id is not None:
            param = [self.Checkpoint(checkpoint=str(snap_id))]
        elif name is not None:
            param = [self.Alias(name=name)]
        else:
            param = []
        body = self.CheckpointQueryParams(*param)
        return self.query_package(body)

    def create_snap(self, name, fs_id, pool_id, snap_size=None):
        pool_param = {'pool': str(pool_id)}
        if snap_size is not None:
            pool_param['size'] = str(snap_size)
        pool = self.StoragePool(**pool_param)
        body = self.NewCheckpoint(
            self.SpaceAllocationMethod(pool),
            checkpointOf=str(fs_id),
            name=name)
        return self.task_package(body)

    def delete_snap(self, snap_id, force=False):
        body = self.DeleteCheckpoint(checkpoint=str(snap_id),
                                     force=str(force).lower())
        return self.task_package(body)

    def create_cifs_server(self, name,
                           mover_id, is_vdm=False,
                           workgroup=None,
                           domain=None,
                           ip_list=None,
                           alias_name=None,
                           local_admin_password=None):
        if domain is not None:
            ret = self._create_domain_cifs_server(
                name, domain, mover_id, is_vdm, ip_list, alias_name,
                local_admin_password)
        elif workgroup is not None:
            ret = self._create_standalone_cifs_server(
                name, workgroup, mover_id, is_vdm, ip_list, alias_name,
                local_admin_password)
        else:
            raise ValueError('either workgroup or domain should be specified.')
        return ret

    def modify_domain_cifs_server(self, name, mover_id, is_vdm=False,
                                  join_domain=None, username=None,
                                  password=None):
        body = self.ModifyW2KCifsServer(
            self.DomainSetting(
                join_domain=converter.boolean_to_str(join_domain),
                username=username, password=password),
            mover=mover_id,
            moverIdIsVdm=converter.boolean_to_str(is_vdm),
            name=name)

        return self.task_package(body)

    def _get_alias_name_li(self, alias_name, name):
        if alias_name is None:
            alias_name = name[-12:]
        alias_name_list = []
        if name != alias_name:
            alias_name_list.append(self.li(alias_name))
        return alias_name_list

    def _create_standalone_cifs_server(self, name, workgroup, mover_id,
                                       is_vdm=False, ip_list=None,
                                       alias_name=None,
                                       local_admin_password=None):
        if local_admin_password is None:
            raise ValueError('local admin password is required for '
                             'stand alone CIFS server.')

        alias_li = self._get_alias_name_li(alias_name, name)

        attributes = {'name': name,
                      'workgroup': workgroup}
        if ip_list is not None:
            attributes['interfaces'] = ip_list
        if local_admin_password is not None:
            attributes['localAdminPassword'] = local_admin_password

        elements = [self.MoverOrVdm(
            mover=str(mover_id),
            moverIdIsVdm=converter.boolean_to_str(is_vdm)
        ),
            self.Aliases(*alias_li)]

        body = self.NewStandaloneCifsServer(*elements, **attributes)
        return self.task_package(body)

    def _create_domain_cifs_server(self, name, domain, mover_id, is_vdm=False,
                                   ip_list=None, alias_name=None,
                                   local_admin_password=None):
        if domain.comp_name is None:
            domain.comp_name = name
        alias_li = self._get_alias_name_li(alias_name, name)

        attributes = {'compName': domain.comp_name,
                      'domain': domain.name,
                      'name': name}
        if ip_list is not None:
            attributes['interfaces'] = ip_list
        if local_admin_password is not None:
            attributes['localAdminPassword'] = local_admin_password

        elements = [self.MoverOrVdm(
            mover=str(mover_id),
            moverIdIsVdm=converter.boolean_to_str(is_vdm)
        ),
            self.Aliases(*alias_li)]
        if domain.user is not None:
            elements.append(self.JoinDomain(userName=domain.user,
                                            password=domain.password))

        body = self.NewW2KCifsServer(*elements, **attributes)
        return self.task_package(body)

    def get_cifs_server(self, name=None, mover_id=None, is_vdm=False):
        params = []
        if mover_id is not None:
            params.append(
                self.MoverOrVdm(mover=str(mover_id),
                                moverIdIsVdm=converter.boolean_to_str(is_vdm)))
        kwargs = {}
        if name is not None:
            kwargs['name'] = name.upper()
        body = self.CifsServerQueryParams(*params, **kwargs)
        return self.query_package(body)

    def delete_cifs_server(self, name, mover_id, is_vdm=False):
        body = self.DeleteCifsServer(
            mover=str(mover_id),
            moverIdIsVdm=converter.boolean_to_str(is_vdm),
            name=name)
        return self.task_package(body)

    def create_dns_domain(self, mover_id, name, servers, protocol='udp'):
        body = self.NewMoverDnsDomain(
            mover=str(mover_id),
            name=name,
            servers=servers,
            protocol=protocol)
        return self.task_package(body)

    def delete_dns_domain(self, mover_id, name):
        body = self.DeleteMoverDnsDomain(
            mover=str(mover_id),
            name=name)
        return self.task_package(body)

    def get_fs_mp(self, path=None, mover_id=None, is_vdm=False):
        param = []
        if mover_id is not None:
            param.append(self.MoverOrVdm(
                mover=str(mover_id),
                moverIdIsVdm=converter.boolean_to_str(is_vdm)))
        kwargs = {}
        if path is not None:
            kwargs['path'] = path
        body = self.MountQueryParams(*param, **kwargs)
        return self.query_package(body)

    def create_fs_mp(self, path, fs_id, mover_id, is_vdm=False):
        body = self.NewMount(
            self.MoverOrVdm(
                mover=str(mover_id),
                moverIdIsVdm=converter.boolean_to_str(is_vdm)),
            fileSystem=str(fs_id),
            path=path)
        return self.task_package(body)

    def delete_fs_mp(self, path, mover_id, is_vdm=False):
        body = self.DeleteMount(
            mover=str(mover_id),
            moverIdIsVdm=converter.boolean_to_str(is_vdm),
            path=path)
        return self.task_package(body)

    def get_mover_host(self, mover_host_id=None):
        aspect = self.AspectSelection(
            **self._props(['moverHosts',
                           'moverMotherboards',
                           'physicalDevices',
                           'fibreChannelConnections']))
        kwargs = {}
        if mover_host_id is not None:
            kwargs['moverHost'] = str(mover_host_id)
        body = self.MoverHostQueryParams(aspect, **kwargs)
        return self.query_package(body)

    def create_mover_interface(self, mover_id, device, ip, net_mask,
                               vlan_id=0, name=None):
        if name is None:
            name = '{}-{}'.format(ip, vlan_id)

        body = self.NewMoverInterface(
            device=device,
            ipAddress=ip,
            mover=str(mover_id),
            name=name,
            netMask=net_mask,
            vlanid=str(vlan_id))
        return self.task_package(body)

    def delete_mover_interface(self, mover_id, ip):
        body = self.DeleteMoverInterface(
            ipAddress=ip,
            mover=str(mover_id))
        return self.task_package(body)

    def create_vdm(self, mover_id, name, pool_id=None):
        params = {'mover': str(mover_id), 'name': name}
        if pool_id is not None:
            params['storagePool'] = str(pool_id)
        return self.task_package(self.NewVdm(**params))

    def delete_vdm(self, vdm_id):
        return self.task_package(self.DeleteVdm(vdm=str(vdm_id)))

    def get_vdm(self, vdm_id=None):
        params = {}
        if vdm_id is not None:
            params['vdm'] = str(vdm_id)
        return self.query_package(self.VdmQueryParams(**params))

    def get_nfs_export(self, mover_id=None, path=None):
        params = {}
        if mover_id is not None:
            params['mover'] = str(mover_id)
        if path is not None:
            params['path'] = path
        return self.query_package(self.NfsExportQueryParams(**params))

    def create_nfs_export(self, mover_id, path, ro=False, host_config=None):
        if host_config is not None:
            param = host_config.get_xml_node()
        else:
            param = []
        body = self.NewNfsExport(mover=str(mover_id), path=path,
                                 readOnly=converter.boolean_to_str(ro),
                                 *param)
        return self.task_package(body)

    def delete_nfs_export(self, mover_id, path):
        body = self.DeleteNfsExport(mover=str(mover_id), path=path)
        return self.task_package(body)

    def list_element(self, name, items):
        f = getattr(self, name)
        li_list = [self.li(i) for i in items]
        return f(*li_list)

    def modify_nfs_export(self, mover_id, path, ro=None, host_config=None):
        if host_config is not None:
            param = host_config.get_xml_node()
        else:
            param = []
        kwargs = {'mover': str(mover_id), 'path': path}
        if ro is not None:
            kwargs['readOnly'] = converter.boolean_to_str(ro)
        body = self.ModifyNfsExport(*param, **kwargs)
        return self.task_package(body)

    def create_cifs_share(self, name, server_name, mover_id,
                          is_vdm=False, path=None):
        if path is None:
            path = r'\{}'.format(name)
        mover = self.MoverOrVdm(mover=str(mover_id),
                                moverIdIsVdm=converter.boolean_to_str(is_vdm))
        body = self.NewCifsShare(mover, self.CifsServers(self.li(server_name)),
                                 name=name, path=path)
        return self.task_package(body)

    def get_cifs_share(self, server_name=None, share_name=None, mover_id=None,
                       is_vdm=False):
        kwargs = {}
        if server_name is not None:
            kwargs['cifsServer'] = server_name
        if share_name is not None:
            kwargs['name'] = share_name
        argv = []
        if mover_id is not None:
            argv.append(self.MoverOrVdm(mover=str(mover_id),
                                        moverIdIsVdm=converter.boolean_to_str(
                                            is_vdm)))
        body = self.CifsShareQueryParams(*argv, **kwargs)
        return self.query_package(body)

    def delete_cifs_share(self, name, mover_id, server_names, is_vdm=False):
        body = self.DeleteCifsShare(
            self.list_element('CifsServers', server_names),
            mover=str(mover_id),
            moverIdIsVdm=converter.boolean_to_str(is_vdm),
            name=name)
        return self.task_package(body)
