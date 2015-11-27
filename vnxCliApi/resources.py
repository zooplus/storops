# coding=utf-8
from __future__ import unicode_literals
from threading import Lock
import re
import six
from vnxCliApi.cli import CliClient, raise_if_err
from vnxCliApi.common import background
from vnxCliApi.enums import \
    VNXProvisionEnum, VNXTieringEnum, VNXSPEnum, VNXPortTypeEnum, VNXError, \
    has_error, VNXMigrationRate
from vnxCliApi.exception import VNXNoHluAvailableError, \
    VNXMigrationError, VNXNoIndexException, VNXAttachSnapError, \
    VNXDetachSnapError, VNXModifyLunError, VNXConsistencyGroupError, \
    VNXSnapError, VNXStorageGroupError, VNXCompressionError, VNXDedupError
from vnxCliApi.parsers import \
    PropDescriptor, get_parser_config
import logging
from past.builtins import filter

LOG = logging.getLogger(__name__)


class VNXResource(object):
    def __init__(self):
        super(VNXResource, self).__init__()
        self._property_cache = {}
        self._parsed_resource = None

    @staticmethod
    def _get(data, key):
        if isinstance(key, PropDescriptor):
            key = key.key
        try:
            ret = data.__getitem__(key)
        except KeyError:
            ret = None
        return ret

    @staticmethod
    def _has_get(data):
        return hasattr(data, '__getitem__')

    @classmethod
    def _get_float_value(cls, data, descriptor):
        if isinstance(data, six.string_types):
            ret = float(data)
        elif cls._has_get(data):
            ret = cls._get(data, descriptor)
        elif isinstance(data, float):
            ret = data
        elif cls._is_int_or_str(data):
            ret = float(data)
        else:
            raise ValueError('Cannot convert input to float.  Value: {}'
                             .format(data))
        return ret

    @staticmethod
    def _is_int_or_str(data):
        is_int = isinstance(data, six.integer_types)
        is_str = isinstance(data, six.text_type)
        return is_int or is_str

    @classmethod
    def _get_integer_value(cls, data, descriptor):
        if isinstance(data, six.string_types):
            ret = int(data)
        elif cls._has_get(data):
            ret = cls._get(data, descriptor)
        elif isinstance(data, float):
            ret = int(round(data))
        elif cls._is_int_or_str(data):
            ret = int(data)
        else:
            raise ValueError('Cannot convert input to integer.  Value: {}'
                             .format(data))
        return ret

    @classmethod
    def _get_text_value(cls, data, *descriptors):
        ret = None
        for descriptor in descriptors:
            if isinstance(data, six.string_types):
                ret = data
            elif cls._has_get(data):
                ret = cls._get(data, descriptor)
            else:
                raise ValueError('Cannot convert input to text.  Value: {}'
                                 .format(data))
            if ret is not None:
                break
        return ret

    def _get_name(self):
        if self._name is not None:
            name = self._name
        else:
            name = self.name
        return name

    @classmethod
    def _get_parser(cls):
        # use class name as the default
        return get_parser_config(cls.__name__)

    def update(self, data=None):
        if data is None:
            data = self._get_raw_resource()

        if isinstance(data, dict):
            self._parsed_resource = data
        else:
            self._parsed_resource = self._parse_cli(data)
        return self

    def get_index(self):
        parser = self._get_parser()
        index_desc = parser.get_index_descriptor()
        if index_desc is not None:
            ret = getattr(self, index_desc.key)
        else:
            raise VNXNoIndexException('{} does not have index.'
                                      .format(self.__class__.__name__))
        return ret

    @property
    def existed(self):
        try:
            ret = self.get_index() is not None
        except VNXNoIndexException:
            # no index, check if any of the property is available
            prop = self._get_first_not_none_prop()
            ret = prop is not None
        return ret

    def _get_first_not_none_prop(self):
        ret = None
        prop_desc_list = self._get_parser().get_all_property_descriptor()
        for prop_desc in prop_desc_list:
            ret = getattr(self, prop_desc.key)
            if ret is not None:
                break
        return ret

    def is_valid(self):
        return self.existed()

    def _get_parsed_resource(self):
        return self._get_raw_resource()

    def _parse_cli(self, data):
        return self._get_parser().parse(data)

    @classmethod
    def parse(cls, output):
        obj = cls()
        data = cls._get_parser().parse_single(output)
        return obj.update(data)

    @classmethod
    def parse_all(cls, output):
        ret = []
        for data in cls._get_parser().parse_all(output):
            obj = cls()
            ret.append(obj.update(data))
        return ret

    def __repr__(self):
        lines = ([self._get_header()] + self._get_properties('    ') +
                 [self._get_tail()])
        return '\n'.join(lines)

    def __str__(self):
        return '{}{}{}'.format(self._get_header(),
                               ', '.join(self._get_properties()),
                               self._get_tail())

    @staticmethod
    def _get_tail():
        return '}>'

    def _get_properties(self, prefix=''):

        def formatted(k, v=None):
            if v is None:
                v = getattr(self, k)
            return '{}{}: {}'.format(prefix, k, v)

        props = [formatted('hash', self.__hash__()),
                 formatted('existed')]
        for mapper in self._get_parser().get_all():
            try:
                props.append(formatted(mapper.key))
            except AttributeError:
                # skip not available attributes
                pass
        return props

    def _get_header(self):
        header = '<{} {{'.format(self.__class__.__name__)
        return header

    @property
    def _cache_size(self):
        return len(self._property_cache)

    def _get_raw_resource(self):
        """get raw input of this resource

        Get the raw input of this resource.
        The input could be retrieved from multiple interface like
        CLI or CIM."""
        return ''

    def __getattr__(self, item):
        try:
            ret = super(object, self).__getattr__(item)
        except AttributeError as ex:
            if item in self._property_cache:
                ret = self._property_cache[item]
            elif item[0] != '_':
                ret = self._get_property_from_raw(item)
            else:
                raise ex
        return ret

    def _get_property_from_raw(self, item):
        ret = None
        parser = self._get_parser()
        if self._parsed_resource is None:
            self.update()
        if parser is not None and self._parsed_resource:
            mapper_key = 'key'
            for property_mapper in parser.get_all():
                key = property_mapper.key
                if key == item:
                    ret = self._parsed_resource[
                        getattr(property_mapper, str(mapper_key))]
                    if property_mapper.cache:
                        self._property_cache[key] = ret
                    break
            else:
                raise AttributeError(
                    "'{}' does not contain attribute '{}'".format(
                        self.__class__.__name__, item))
        return ret

    def _is_client_available(self):
        return '_cli' in dir(self) and getattr(self, '_cli') is not None


class VNXResourceList(VNXResource):
    def __init__(self):
        super(VNXResourceList, self).__init__()
        self._list = []
        self._iter = None

    def update(self, data=None):
        if data is None:
            data = self._get_raw_resource()

        if data is not None and isinstance(data, dict):
            parsed_list = data
        else:
            parsed_list = self._parse_cli(data)

        for i in parsed_list:
            item = self.get_resource_class()()
            item.update(i)
            self._list.append(item)
        return self

    def _parse_cli(self, data):
        return self._get_parser().parse_all(data)

    @classmethod
    def _get_parser(cls):
        return get_parser_config(cls.get_resource_class().__name__)

    @property
    def list(self):
        if not self._list:
            self.update()
        return self._list

    @classmethod
    def get_resource_class(cls):
        raise NotImplementedError(
            'should return the class ref of the resource in the list.')

    def _join_item_repr(self):
        return '\n'.join(map(lambda i: i.__repr__(), self.list))

    def _join_item_str(self):
        return ', '.join(map(lambda i: i.__str__(), self.list))

    def __str__(self):
        return '{}{}{}'.format(self._get_header(),
                               self._join_item_str(),
                               self._get_tail())

    def __repr__(self):
        return '{}\n{}\n{}'.format(self._get_header(),
                                   self._join_item_repr(),
                                   self._get_tail())

    def __len__(self):
        return len(self.list)

    def __iter__(self):
        self._iter = self.list.__iter__()
        return self

    def next(self):
        return six.next(self._iter)

    def __next__(self):
        return self.next()

    def __getitem__(self, item):
        return self.list[item]


# noinspection PyAbstractClass
class VNXCliResourceList(VNXResourceList):
    def __init__(self, cli=None):
        super(VNXCliResourceList, self).__init__()
        self._cli = cli

    def update(self, data=None):
        ret = super(VNXCliResourceList, self).update(data)
        for item in self._list:
            item._cli = self._cli
        return ret


class VNXDomainMemberList(VNXCliResourceList):
    def _get_member(self, index):
        def filter_by_sp_name(member):
            sp = VNXSPEnum.from_str(member.name)
            return sp == index

        result = filter(filter_by_sp_name, self.list)
        ret = None
        if len(result) > 0:
            ret = result[0]
        return ret

    @property
    def spa(self):
        return self._get_member(VNXSPEnum.SP_A)

    @property
    def spb(self):
        return self._get_member(VNXSPEnum.SP_B)

    @property
    def control_station(self):
        return self._get_member(VNXSPEnum.CONTROL_STATION)

    @classmethod
    def get_resource_class(cls):
        return VNXDomainMember

    def _get_raw_resource(self):
        return self._cli.get_domain()


class VNXDomainMember(VNXResource):
    @property
    def ip(self):
        ret = 'N/A'
        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', self.ip_address)
        if len(ip) > 0:
            ret = ip[0]
        return ret

    @property
    def is_master(self):
        return 'Master' in self.ip_address


class VNXSystem(VNXResource):
    def __init__(self, ip=None, username=None, password=None,
                 heartbeat_interval=None):
        super(VNXSystem, self).__init__()
        self._cli = CliClient(ip, username, password,
                              heartbeat_interval=heartbeat_interval)
        self._dml = VNXDomainMemberList(self._cli)
        background(self._update_nodes_ip)

    def _update_nodes_ip(self):
        self._dml.update()
        self._cli.set_ip(self.spa_ip, self.spb_ip, self.control_station_ip)

    @property
    def spa_ip(self):
        return self._dml.spa.ip

    @property
    def spb_ip(self):
        return self._dml.spb.ip

    @property
    def control_station_ip(self):
        return self._dml.control_station.ip

    def _get_raw_resource(self):
        return self._cli.get_agent()

    def get_pool(self, pool_id=None, name=None):
        return VNXPool.get(pool_id=pool_id, name=name, cli=self._cli)

    def get_lun(self, lun_id=None, name=None):
        return VNXLun.get(self._cli, lun_id=lun_id, name=name)

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

    def remove_snap(self, name):
        VNXSnap(name, self._cli).remove()

    def create_sg(self, name):
        return VNXStorageGroup.create(name, self._cli)

    def remove_sg(self, name):
        VNXStorageGroup(name, self._cli).remove()

    def create_cg(self, name, members=None):
        return VNXConsistencyGroup.create(self._cli, name=name,
                                          members=members)

    def remove_cg(self, name):
        VNXConsistencyGroup(name, self._cli).remove()


class VNXPoolList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXPool

    def _get_raw_resource(self):
        return self._cli.get_pool()


class VNXPool(VNXResource):
    def __init__(self, pool_id=None, name=None, cli=None):
        super(VNXPool, self).__init__()
        self._cli = cli
        self._pool_id = pool_id
        self._name = name

    @classmethod
    def get(cls, cli, pool_id=None, name=None):
        if pool_id is None and name is None:
            ret = VNXPoolList(cli)
        else:
            ret = VNXPool(pool_id, name, cli)
        return ret

    def create_lun(self,
                   lun_name,
                   size_gb=1,
                   lun_id=None,
                   provision=None,
                   tier=None):
        ret = self._cli.create_pool_lun(
            pool_id=self.pool_id,
            lun_name=lun_name,
            lun_id=lun_id,
            size=size_gb,
            provision=provision,
            tier=tier)
        if len(ret.strip()) > 0:
            raise ValueError('error creating lun: {}'.format(ret))
        return VNXLun(lun_id, lun_name, self._cli)

    @staticmethod
    def remove_lun(lun, remove_snapshots=False, force_detach=False):
        lun.remove(remove_snapshots, force_detach)

    def _get_raw_resource(self):
        return self._cli.get_pool(name=self._name, pool_id=self._pool_id)

    def get_lun(self):
        lun_list = VNXLun.get(self._cli)
        return [l for l in lun_list if l.pool_name == self.name]


class VNXLunList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXLun

    def _get_raw_resource(self):
        return self._cli.get_lun()


class VNXLun(VNXResource):
    DEFAULT_TIER = VNXTieringEnum.HIGH_AUTO
    DEFAULT_PROVISION = VNXProvisionEnum.THICK

    def __init__(self, lun_id=None, name=None, cli=None):
        super(VNXLun, self).__init__()
        self._cli = cli
        self._lun_id = lun_id
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_lun(name=self._name, lun_id=self._lun_id)

    @staticmethod
    def create(cli,
               pool_id=None,
               pool_name=None,
               lun_id=None,
               lun_name=None,
               size_gb=1,
               provision=None,
               tier=None):
        pool = VNXPool(pool_id, pool_name, cli)
        return pool.create_lun(lun_name, size_gb, lun_id, provision, tier)

    def create_mount_point(self, mount_point_id=None, mount_point_name=None):
        lun_id = self.get_id(self)
        self._cli.create_mount_point(primary_lun_id=lun_id,
                                     mount_point_name=mount_point_name,
                                     mount_point_id=mount_point_id)
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
                                   new_tier=new_tier)
        msg = 'error change lun tier.'
        raise_if_err(out, VNXModifyLunError, msg)

    @property
    def provision(self):
        ret = self.DEFAULT_PROVISION
        try:
            if self.is_thin_lun:
                ret = VNXProvisionEnum.THIN
            if self.is_compressed:
                ret = VNXProvisionEnum.COMPRESSED
            elif self.dedup_state:
                ret = VNXProvisionEnum.DEDUPED
        except AttributeError:
            pass
        return ret

    @staticmethod
    def get(cli, lun_id=None, name=None):
        if lun_id is None and name is None:
            ret = VNXLunList(cli)
        else:
            ret = VNXLun(lun_id, name, cli)
        return ret

    def create_snap(self, name, allow_rw=None, auto_delete=None):
        self._cli.create_snap(self.lun_id, name, allow_rw, auto_delete)
        return VNXSnap(name, self._cli)

    def attach_snap(self, snap):
        snap_name = VNXSnap.get_name(snap)
        out = self._cli.attach_snap(snap_name, lun_id=self.get_id(self))
        if len(out):
            raise VNXAttachSnapError(out)

    def detach_snap(self):
        out = self._cli.detach_snap(lun_id=self.get_id(self))
        if len(out):
            raise VNXDetachSnapError(out)

    def get_snap(self, name=None):
        if name is not None:
            ret = VNXSnap.get(self._cli, name)
        else:
            snaps = VNXSnap.get(self._cli)
            ret = [s for s in snaps if self.lun_id in s.source_luns]
        return ret

    def remove_snap(self, name):
        VNXSnap(name, self._cli).remove()

    def migrate(self, tgt, rate=VNXMigrationRate.HIGH):
        tgt_id = self.get_id(tgt)
        src_id = self.get_id(self)
        out = self._cli.migrate_lun(src_id, tgt_id, rate)
        if len(out) > 0:
            raise VNXMigrationError(out)

    def expand(self, new_size, ignore_thresholds=False):
        out = self._cli.expand_pool_lun(new_size, self.get_id(self),
                                        ignore_thresholds=ignore_thresholds)
        raise_if_err(out, VNXModifyLunError,
                     'failed to expand lun.')

    def cancel_migrate(self):
        src_id = self.get_id(self)
        out = self._cli.cancel_migrate_lun(src_id)
        if len(out) > 0:
            raise VNXMigrationError(out)

    def get_migration_session(self):
        return VNXMigrationSession.get(self._cli, self)

    @staticmethod
    def get_id(lun):
        if isinstance(lun, VNXLun):
            if lun._lun_id is not None:
                lun = lun._lun_id
            else:
                lun = lun.lun_id
        elif isinstance(lun, six.string_types) and lun.isdigit():
            lun = int(lun)
        if not isinstance(lun, int):
            raise ValueError('invalid lun number supplied: {}'
                             .format(lun))
        return lun

    @classmethod
    def get_id_list(cls, *lun_list):
        return list(map(cls.get_id, lun_list))

    def remove(self, remove_snapshots=False, force_detach=False):
        self._cli.remove_pool_lun(self.get_id(self),
                                  remove_snapshots=remove_snapshots,
                                  force_detach=force_detach)

    def rename(self, new_name):
        if new_name is not None and self._name != new_name:
            out = self._cli.modify_lun(lun_id=self._lun_id,
                                       lun_name=self._name,
                                       new_name=new_name)
            raise_if_err(out, VNXModifyLunError,
                         'failed to change lun name.')
            self._name = new_name

    def __setattr__(self, key, value):
        if self._is_client_available():
            if key == 'name':
                self.rename(value)
            elif key == 'is_compressed':
                if value:
                    self.enable_compression()
                else:
                    self.disable_compression()
            elif key == 'is_dedup':
                self._update_dedup_state(value)
        super(VNXLun, self).__setattr__(key, value)

    def enable_compression(self, rate=None, ignore_thresholds=None):
        lun_id = self.get_id(self)
        out = self._cli.enable_compression(lun_id, rate, ignore_thresholds)
        raise_if_err(out, VNXCompressionError,
                     'failed to enable compression on {}.'.format(lun_id))

    def disable_compression(self, ignore_thresholds=None):
        lun_id = self.get_id(self)
        out = self._cli.disable_compression(lun_id, ignore_thresholds)
        raise_if_err(out, VNXCompressionError,
                     'failed to disable compression on {}.'.format(lun_id))

    def _update_dedup_state(self, tgt_state):
        out = self._cli.modify_lun(lun_id=self._lun_id,
                                   lun_name=self._name,
                                   dedup=tgt_state)
        raise_if_err(out, VNXDedupError,
                     'failed to set dedup state to {} for {}.'
                     .format(tgt_state, self.get_id(self)))

    def enable_dedup(self):
        self._update_dedup_state(True)

    def disable_dedup(self):
        self._update_dedup_state(False)


class VNXSnapList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXSnap

    def _get_raw_resource(self):
        return self._cli.get_snap()


class VNXSnap(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXSnap, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_snap(name=self._name)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXSnapList(cli)
        else:
            ret = VNXSnap(name, cli)
        return ret

    def remove(self):
        self._cli.remove_snap(self._get_name())

    def copy(self, new_name,
             ignore_migration_check=False,
             ignore_dedup_check=False):
        name = self._get_name()
        out = self._cli.copy_snap(name, new_name,
                                  ignore_migration_check,
                                  ignore_dedup_check)
        raise_if_err(out, VNXSnapError,
                     'failed to copy snap {}.'.format(name))
        return VNXSnap(name=new_name, cli=self._cli)

    def modify(self, new_name=None, desc=None,
               auto_delete=None, rw=None):
        name = self._get_name()
        out = self._cli.modify_snap(name, new_name, desc, auto_delete, rw)
        raise_if_err(out, VNXSnapError,
                     'failed to modify snap {}.'.format(name))
        if new_name is not None:
            self._name = new_name

    @staticmethod
    def get_name(snap):
        if isinstance(snap, VNXSnap):
            if snap._name is not None:
                ret = snap._name
            else:
                ret = snap.name
        elif isinstance(snap, six.string_types):
            ret = snap
        else:
            raise ValueError('invalid snap.')
        return ret


class VNXMigrationSessionList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXMigrationSession

    def _get_raw_resource(self):
        return self._cli.get_migration_session()


class VNXMigrationSession(VNXResource):
    def __init__(self, source=None, cli=None):
        super(VNXMigrationSession, self).__init__()
        self._cli = cli
        self._source = source

    def _get_raw_resource(self):
        source_id = VNXLun.get_id(self._source)
        return self._cli.get_migration_session(source_id)

    @classmethod
    def get(cls, cli, source=None):
        if source is None:
            ret = VNXMigrationSessionList(cli)
        else:
            ret = VNXMigrationSession(source, cli)
        return ret


class VNXConsistencyGroupList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXConsistencyGroup

    def _get_raw_resource(self):
        return self._cli.get_cg()


class VNXConsistencyGroup(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXConsistencyGroup, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_cg(name=self._name)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXConsistencyGroupList(cli)
        else:
            ret = VNXConsistencyGroup(name, cli)
        return ret

    @classmethod
    def create(cls, cli, name, members=None, auto_delete=None):
        cli.create_cg(name, members, auto_delete)
        return VNXConsistencyGroup(name=name, cli=cli)

    def remove(self):
        name = self._get_name()
        out = self._cli.remove_cg(name)
        raise_if_err(out, VNXConsistencyGroupError,
                     'error remove cg "{}".'.format(name))

    def _cg_member_op(self, op, lun_list):
        id_list = VNXLun.get_id_list(*lun_list)
        name = self._get_name()
        out = op(name, *id_list)
        raise_if_err(out, VNXConsistencyGroupError,
                     'error change member of "{}".'.format(name))

    def add_member(self, *lun_list):
        self._cg_member_op(self._cli.add_cg_member, lun_list)

    def remove_member(self, *lun_list):
        self._cg_member_op(self._cli.remove_cg_member, lun_list)

    def replace_member(self, *lun_list):
        self._cg_member_op(self._cli.replace_cg_member, lun_list)


class VNXSPPortList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXSPPort

    def _get_raw_resource(self):
        return self._cli.get_sp_port()


class VNXSPPort(VNXResource):
    def __init__(self, sp=None, port_id=None, cli=None):
        super(VNXSPPort, self).__init__()
        self._cli = cli
        self._sp = sp
        self._port_id = port_id

    def _get_raw_resource(self):
        raise ValueError('Cannot get single sp port info from cli.  '
                         'Use {}.get_port(sp, id, cli) instead.'
                         .format(self.__class__.__name__))

    @classmethod
    def get(cls, cli, sp=None, port_id=None):

        ret = VNXSPPortList(cli)
        if sp is not None:
            ret = filter(lambda p: p.sp == sp, ret)

        if port_id is not None:
            ret = filter(lambda p: p.port_id == port_id, ret)

        if sp is not None and port_id is not None and len(ret) == 1:
            ret = ret[0]

        return ret


class VNXPort(VNXResource):
    @classmethod
    def _get_parser(cls):
        pass

    def __init__(self):
        super(VNXPort, self).__init__()
        self._sp = None
        self._number = None
        self._type = VNXPortTypeEnum.FC
        self._host_initiator_list = []

    def is_valid(self):
        return self.sp is not None and self.number is not None

    @property
    def sp(self):
        return self._sp

    @sp.setter
    def sp(self, value):
        if len(value) == 1:
            value = 'SP {}'.format(value.upper())

        if value in VNXSPEnum.get_all():
            self._sp = value
        else:
            LOG.warning('{} is not a valid sp.'.format(value))

    def get_sp_index(self):
        ret = None
        if self.sp is not None:
            ret = self.sp[-1]
        return ret

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, value):
        if not isinstance(value, int):
            try:
                self._number = int(value)
            except ValueError:
                LOG.warning('{} is not a valid port number.'
                            .format(value))
        else:
            self._number = value

    @property
    def type(self):
        return self._type

    @property
    def host_initiator_list(self):
        return tuple(self._host_initiator_list)

    @staticmethod
    def create(sp, number, port_type=VNXPortTypeEnum.FC):
        port = VNXPort()
        port.sp = sp
        port.number = number
        port._type = port_type
        return port

    @staticmethod
    def from_storage_group_hba(sg_hba):
        port = VNXPort.create(sg_hba.hba[1], int(sg_hba.hba[2]))
        if '.' in sg_hba.hba[0]:
            port._type = VNXPortTypeEnum.ISCSI
        elif ':' in sg_hba.hba[0]:
            port._type = VNXPortTypeEnum.FC
        port._host_initiator_list.append(sg_hba.hba[0])
        return port

    def as_tuple(self):
        return self.sp, self.number

    def __repr__(self):
        return ('<VNXPort {{'
                'SP: {}, '
                'Number: {},'
                'Host Initiator List: {}}}>'
                .format(self.sp, self.number, self.host_initiator_list))

    def __hash__(self):
        return hash('<VNXPort {{'
                    'SP: {}, '
                    'Number: {}}}'.format(self.sp, self.number))

    def __eq__(self, other):
        return self.sp == other.sp and self.number == other.number


class VNXStorageGroup(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXStorageGroup, self).__init__()
        self._cli = cli
        self._name = name

        self._uid = ''
        self._hba_port_map = []
        self._conn = None
        self._hlu_lock = Lock()

    def _get_raw_resource(self):
        return self._cli.get_sg(name=self._name)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXStorageGroupList(cli)
        else:
            ret = VNXStorageGroup(name, cli)
        return ret

    @classmethod
    def create(cls, name, cli):
        cli.create_sg(name)
        return VNXStorageGroup(name, cli)

    def remove(self):
        self._cli.remove_sg(self._get_name())

    def has_hlu(self, hlu):
        return hlu in self.alu_hlu_map.values()

    def has_alu(self, lun):
        alu = VNXLun.get_id(lun)
        return alu in self.alu_hlu_map.keys()

    def get_hlu(self, lun):
        alu = VNXLun.get_id(lun)
        return self.alu_hlu_map.get(alu, None)

    def is_valid(self):
        return len(self.name) > 0 and len(self.uid) > 0

    @property
    def hba_port_map(self):
        if not self._hba_port_map:
            self.hba_port_map = self.hba_sp_pairs
        return self._hba_port_map

    @hba_port_map.setter
    def hba_port_map(self, hba_sp_pairs):
        def _process_cli_output(value):
            port = VNXPort.from_storage_group_hba(value)
            hba = value.uid
            self._hba_port_map.append((hba, port))

        if hba_sp_pairs is not None:
            for item in hba_sp_pairs:
                _process_cli_output(item)

    @property
    def port_list(self):
        return tuple(set(map(lambda x: x[1], self.hba_port_map)))

    @property
    def initiator_uid_list(self):
        return tuple(set(map(lambda x: x.uid, self.hba_sp_pairs)))

    def get_initiator_uids(self, port_type=None):
        ret = []
        for hba, port in self.hba_port_map:
            if port_type is not None:
                if port.type == port_type:
                    ret.append(hba)
            else:
                ret.append(hba)
        return tuple(set(ret))

    def get_ports(self, initiator_uid):
        ret = []
        for hba, port in self.hba_port_map:
            if hba == initiator_uid:
                ret.append(port)
        return tuple(set(ret))

    _hlu_full = None
    _max_hlu = 255

    @classmethod
    def get_max_luns_per_sg(cls):
        return cls._max_hlu

    @classmethod
    def set_max_luns_per_sg(cls, value):
        LOG.info('Update max LUNs per storage group to: {}'
                 .format(value))
        cls._max_hlu = value
        cls._hlu_full = None

    @classmethod
    def _hlu_full_set(cls):
        if cls._hlu_full is None:
            cls._hlu_full = set(range(1, cls.get_max_luns_per_sg() + 1))
        return set(cls._hlu_full)

    def _get_hlu_to_add(self, alu):
        ret = None
        with self._hlu_lock:
            remain = self._hlu_full_set() - set(self.alu_hlu_map.values())
            if len(remain) == 0:
                raise VNXNoHluAvailableError(
                    'no hlu number available for attach.')
            ret = remain.pop()
            self.alu_hlu_map[alu] = ret
        return ret

    def _remove_alu(self, alu):
        ret = None
        with self._hlu_lock:
            if self.has_alu(alu):
                ret = self.alu_hlu_map.pop(alu)
        return ret

    class _HluOccupiedError(Exception):
        pass

    def attach_hlu(self, lun):
        lun = VNXLun.get_id(lun)
        while True:
            alu = self._get_hlu_to_add(lun)
            out = self._cli.sg_add_hlu(self._get_name(), alu, lun)
            if has_error(out, VNXError.SG_HOST_LUN_USED):
                self.update()
                continue
            break
        return VNXLun(self._cli, lun)

    def detach_hlu(self, lun):
        alu = VNXLun.get_id(lun)
        out = self._cli.sg_remove_hlu(self._get_name(), alu)
        raise_if_err(out, VNXStorageGroupError,
                     'failed to detach alu {}.'.format(alu))
        self._remove_alu(alu)

    def connect_host(self, host):
        out = self._cli.sg_connect_host(self._get_name(), host)
        raise_if_err(out, VNXStorageGroupError,
                     'failed to connect host {}.'.format(host))

    def disconnect_host(self, host):
        out = self._cli.sg_disconnect_host(self._get_name(), host)
        raise_if_err(out, VNXStorageGroupError,
                     'failed to disconnect host {}.'.format(host))

    @property
    def uid(self):
        return self.wwn


class VNXNduList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXNdu

    def _get_raw_resource(self):
        return self._cli.get_ndu()


class VNXNdu(VNXResource):
    def __init__(self, name=None, cli=None):
        super(VNXNdu, self).__init__()
        self._cli = cli
        self._name = name

    def _get_raw_resource(self):
        return self._cli.get_ndu(name=self._name)

    @classmethod
    def get(cls, cli, name=None):
        if name is None:
            ret = VNXNduList(cli)
        else:
            ret = VNXNdu(name, cli)
        return ret


class VNXStorageGroupList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXStorageGroup

    def __init__(self, cli=None):
        super(VNXStorageGroupList, self).__init__(cli)
        self._sg_map = {}

    def add_sg(self, sg):
        self._sg_map[sg.name] = sg

    def _get_raw_resource(self):
        return self._cli.get_sg()


class VNXStorageGroupHBA(VNXResource):
    @property
    def sp(self):
        return VNXSPEnum.from_str(self.hba[1])

    @property
    def port_id(self):
        return int(self.hba[2])

    @property
    def uid(self):
        return self.hba[0]

    @property
    def vlan(self):
        ret = None
        sp_port = self.sp_port
        if 'v' in sp_port:
            ret = int(sp_port[sp_port.find('v') + 1:])
        return ret

    @property
    def port_type(self):
        ret = None
        if '.' in self.uid:
            ret = VNXPortTypeEnum.ISCSI
        elif ':' in self.uid:
            ret = VNXPortTypeEnum.FC
        return ret


class VNXStorageGroupHBAList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXStorageGroupHBA


class VNXPoolFeature(VNXResource):
    def __init__(self, cli=None):
        super(VNXPoolFeature, self).__init__()
        self._cli = cli

    def _get_raw_resource(self):
        return self._cli.get_pool_feature()


class VNXConnectionPortList(VNXCliResourceList):
    @classmethod
    def get_resource_class(cls):
        return VNXConnectionPort

    def _get_raw_resource(self):
        return self._cli.get_connection_port()


class VNXConnectionPort(VNXResource):
    def __init__(self, sp=None, port_id=None, vport_id=None, cli=None):
        super(VNXConnectionPort, self).__init__()
        if sp is None:
            sp = VNXSPEnum.SP_A
        self._sp = sp
        self._port_id = port_id
        self._vport_id = vport_id
        self._cli = cli

    def _get_raw_resource(self):
        return self._cli.get_connection_port(
            sp=self._sp, port_id=self._port_id, vport_id=self._vport_id)

    @classmethod
    def get(cls, cli, sp=None, port_id=None, vport_id=None):
        if sp is not None and port_id is not None and vport_id is not None:
            ret = VNXConnectionPort(sp, port_id, vport_id, cli)
        else:
            ret = VNXConnectionPortList(cli)

            if sp is not None:
                ret = filter(lambda p: p.sp == sp, ret)

            if port_id is not None:
                ret = filter(lambda p: p.port_id == port_id, ret)

            if port_id is not None:
                ret = filter(lambda p: p.virtual_port_id == vport_id,
                             ret)
        return ret
