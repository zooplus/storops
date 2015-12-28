# coding=utf-8
from __future__ import unicode_literals
import logging
import os
from datetime import datetime
from subprocess import Popen, PIPE
from time import sleep, time

import six
from retryz import retry

from vnxCliApi.common import Cache, daemon, WeightedAverage, check_text, \
    check_int, check_enum
from vnxCliApi.enums import VNXSPEnum, VNXTieringEnum, VNXProvisionEnum, \
    VNXMigrationRate, has_error, VNXCompressionRate, VNXError
from vnxCliApi import exception as ex

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


def command(f):
    def func_wrapper(self, *argv, **kwargs):
        no_poll = not kwargs.get('poll', True)
        kwargs.pop('poll', None)
        commands = f(self, *argv, **kwargs)
        if isinstance(commands, six.string_types):
            commands = commands.split()
        commands = list(commands)
        if no_poll:
            commands.insert(0, '-np')
        out = self.execute(commands)
        return out

    return func_wrapper


def _text_var(name, value):
    return [name, check_text(value)]


def _int_var(name, value):
    return [name, check_int(value)]


def _enum_var(name, value, enum_class):
    return [name, check_enum(value, enum_class)]


def raise_if_err(out, ex_clz=None, msg=None, expected_error=None):
    def on_error():
        log.error(msg)
        raise ex_clz(msg)

    if msg is None:
        msg = out
    else:
        msg = '{}  node detail:\n{}'.format(msg, out)
    if ex_clz is None:
        ex_clz = ValueError
    if expected_error is None or len(expected_error) == 0:
        # check if out is empty
        if out is not None and len(out) > 0:
            on_error()
    else:
        if not isinstance(expected_error, (list, tuple)):
            expected_error = [expected_error]
        if has_error(out, *expected_error):
            on_error()


class NaviCommand(object):
    def __init__(self, username=None, password=None, scope=0,
                 sec_file=None, timeout=None):
        self._username = username
        self._password = password
        self._scope = scope
        self._sec_file = sec_file
        self._timeout = timeout

    @property
    def timeout(self):
        return self._timeout

    def get_credentials(self):
        if self._username is None and self._password is None:
            # use security file
            if self._sec_file is not None:
                ret = _text_var('-secfilepath', self._sec_file)
            else:
                ret = []
        elif self._username is None or self._password is None:
            raise ValueError('username or password missing.')
        else:
            ret = ['-user', self._username,
                   '-password', self._password,
                   '-scope', self._scope]
        if self.timeout is not None:
            ret += _int_var('-t', self.timeout)
        return ret

    _cli_binary_candidates = (
        r'/opt/Navisphere/bin/naviseccli',
        r'C:\Program Files (x86)\EMC\Navisphere CLI\naviseccli.exe',
        r'C:\Program Files\EMC\Navisphere CLI\naviseccli.exe')

    @classmethod
    @Cache.cache()
    def _get_binary(cls):
        binary = 'naviseccli'
        for c in cls._cli_binary_candidates:
            if os.path.exists(c):
                binary = c
                break
        return binary

    def _get_cmd_prefix(self, ip):
        binary = self._get_binary()
        return [binary, '-h', ip] + self.get_credentials()

    def execute(self, cmd, raise_on_rc=None, check_rc=False):
        cmd = list(map(six.text_type, cmd))
        cmd_str = ' '.join(cmd)
        log.debug('call command: %s', cmd_str)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output = p.stdout.read()
        p.poll()
        rc = p.returncode
        if rc is not None:
            if rc == raise_on_rc or (check_rc and rc != 0):
                raise ValueError('raise error on return code "{}".'
                                 .format(rc))
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        return output.strip()


class NodeInfo(object):
    def __init__(self, name, ip, available=None, working=False):
        """ constructor for `NodeInfo`.

        :param name: name of the node, could be `spa`, or `spb`
        :param ip: ip address of the node
        :param available: indicate whether this node is alive.
        :param working: indicate whether this node is executing command.
        :return:
        """
        self.name = VNXSPEnum.from_str(name)
        self.ip = ip
        self._available = available
        self.timestamp = None
        self.working = working
        self._latency = WeightedAverage()

    @property
    def available(self):
        return self._available

    @available.setter
    def available(self, available):
        self._available = available
        self.timestamp = datetime.now()

    @property
    def latency(self):
        return self._latency.value()

    @latency.setter
    def latency(self, value):
        self._latency.add(value)

    def __repr__(self):
        props_to_print = ['name', 'ip', 'available',
                          'working', 'latency', 'timestamp']
        info = ', '.join(['{}: {}'.format(p, getattr(self, p))
                          for p in props_to_print])
        return info

    def __str__(self):
        return self.__repr__()


class _NodeInfoMap(object):
    def __init__(self):
        self._map = dict()

    def update(self, node):
        if not isinstance(node, NodeInfo):
            raise ValueError('input must be an instance of _NodeInfo.')
        self._map[node.name] = node

    def is_available(self, name):
        ret = False
        name = VNXSPEnum.from_str(name)
        if name in self._map:
            ret = self._map[name].available
        return ret

    def nodes(self):
        return list(self._map.values())

    def update_by_ip(self, ip, available=None, working=None, latency=None):
        node = self.get_node_by_ip(ip)
        if node is not None:
            if available is not None:
                node.available = available
            if working is not None:
                node.working = working
            if latency is not None:
                node.latency = latency

    def get_node_by_ip(self, ip):
        ret = None
        for node in self.nodes():
            if node.ip == ip:
                ret = node
                break
        return ret

    def __repr__(self):
        ret = 'node count: {}, detail: \n'.format(len(self._map))
        ret += '\n'.join(map(six.text_type, self._map.values()))
        return ret

    def __str__(self):
        return self.__repr__()


class NodeHeartBeat(NaviCommand):
    def __init__(self, username=None, password=None, scope=0,
                 interval=60, timeout=30):
        super(NodeHeartBeat, self).__init__(username, password, scope,
                                            timeout=timeout)
        self._node_map = _NodeInfoMap()
        self._interval = interval
        self._heartbeat_thread = None
        if interval > 0:
            self._heartbeat_thread = daemon(self._run)
        self.command_count = 0

    def reset(self):
        self._node_map = _NodeInfoMap()
        self.command_count = 0

    def _get_sp_by_category(self):
        available_sp = []
        unavailable_sp = []
        unknown_sp = []
        nodes = self._node_map.nodes()
        for node in nodes:
            if VNXSPEnum.is_sp(node.name):
                if node.available is None:
                    unknown_sp.append(node)
                elif node.available:
                    available_sp.append(node)
                else:
                    unavailable_sp.append(node)
        return available_sp, unavailable_sp, unknown_sp

    def get_alive_sp_ip(self):
        def get_sp_from_list(sp_list):
            for s in sp_list:
                if not s.working:
                    r = s.ip
                    break
            else:
                # both working, pick random
                r = sp_list[0].ip
            return r

        available, unavailable, unknown = self._get_sp_by_category()
        if len(unavailable) == 2 or len(available) == 0 and len(unknown) == 0:
            raise ex.VNXSystemDownError(
                'both storage processors are not available.')
        elif len(available) > 0:
            ret = get_sp_from_list(available)
        else:
            ret = get_sp_from_list(unknown)
        return ret

    def heart_beat(self):
        list(map(self._ping_node, self.nodes))

    @property
    def interval(self):
        return self._interval

    def _run(self):
        while self.interval > 0:
            self.heart_beat()
            sleep(self.interval)
        self._heartbeat_thread = None

    @property
    def nodes(self):
        return self._node_map.nodes()

    @interval.setter
    def interval(self, value):
        self._interval = value
        if self._heartbeat_thread is None:
            # there is no loop check
            self._heartbeat_thread = daemon(self._run)

    def execute_cmd(self, ip, cmd):
        self.update_by_ip(ip, working=True)
        start = time()
        out = self.execute(cmd)
        if VNXError.sp_not_available(out):
            available = False
            latency = None
        else:
            available = True
            latency = time() - start
        self.update_by_ip(ip, available, False, latency)
        self.command_count += 1

        if latency is None:
            msg = '{} is not available.'.format(ip)
            log.warn(msg)
            raise ex.VNXSPDownError(msg)
        return out

    def _ping_sp(self, ip):
        cmd = self._get_cmd_prefix(ip)
        timeout = self.timeout
        if timeout is not None:
            latency = self.get_latency(ip)
            if latency is not None:
                timeout += latency
            cmd += ['-t', timeout]
        cmd += ['-np', 'getagent']
        return self.execute_cmd(ip, cmd)

    def _ping_node(self, node):
        def do():
            self._ping_sp(node.ip)

        if VNXSPEnum.is_sp(node.name) and not node.working:
            daemon(do)

    def is_available(self, name):
        return self._node_map.is_available(name)

    def add(self, name, ip, available=None, working=False):
        if name is not None:
            node = NodeInfo(name, ip, available, working)
            self._node_map.update(node)

    def update_by_ip(self, ip, available=None, working=None, latency=None):
        self._node_map.update_by_ip(ip, available, working, latency)

    def get_latency(self, ip):
        node = self.get_node_by_ip(ip)
        ret = None
        if node is not None:
            ret = node.latency
        return ret

    def get_node_by_ip(self, ip):
        return self._node_map.get_node_by_ip(ip)

    def __repr__(self):
        return ('check interval: {}(seconds), total check count: {}, '
                'command timeout: {}(seconds), {}'
                .format(self.interval, self.command_count, self.timeout,
                        self._node_map))

    def __str__(self):
        return self.__repr__()


class CliClient(NaviCommand):
    def __init__(self, ip=None,
                 username=None, password=None, scope=0,
                 sec_file=None,
                 timeout=None,
                 heartbeat_interval=None):
        super(CliClient, self).__init__(username, password, scope,
                                        sec_file, timeout)

        if heartbeat_interval is None:
            heartbeat_interval = 60
        self._heart_beat = NodeHeartBeat(interval=heartbeat_interval,
                                         timeout=timeout)
        self._heart_beat.add(VNXSPEnum.SP_A, ip)

    def set_ip(self, spa, spb=None, cs=None):
        self._heart_beat.add(VNXSPEnum.SP_A, spa)
        self._heart_beat.add(VNXSPEnum.SP_B, spb)
        self._heart_beat.add(VNXSPEnum.CONTROL_STATION, cs)

    @property
    def heartbeat(self):
        return self._heart_beat

    @command
    def get_agent(self):
        return 'getagent'

    @command
    def get_domain(self):
        return 'domain -list'

    @command
    def get_pool(self, name=None, pool_id=None):
        cmd = 'storagepool -list -all'.split()
        if name is not None:
            cmd += _text_var('-name', name)
        elif pool_id is not None:
            cmd += _int_var('-id', pool_id)
        return cmd

    @command
    def get_lun(self, name=None, lun_id=None):
        cmd = 'lun -list -all'.split()
        cmd += self._get_lun_opt(lun_id, name, allow_empty=True)
        return cmd

    @command
    def get_cg(self, name=None):
        cmd = 'snap -group -list'.split()
        if name is not None:
            cmd += _text_var('-id', name)
        cmd.append('-detail')
        return cmd

    @command
    def get_sp_port(self):
        return 'port -list -sp -all'

    @command
    def get_connection_port(self, sp=None, port_id=None, vport_id=None):
        cmd = 'connection -getport -all'.split()
        if sp is not None:
            cmd += ['-sp', VNXSPEnum.get_sp_index(sp)]

        if port_id is not None:
            cmd += _int_var('-portid', port_id)
            if vport_id is not None:
                cmd += _int_var('-vportid', vport_id)

        return cmd

    @command
    def get_sg(self, name=None):
        cmd = 'storagegroup -list -host -iscsiAttributes'.split()
        if name is not None:
            cmd += _text_var('-gname', name)
        return cmd

    @command
    def get_pool_feature(self):
        return 'storagepool -feature -info -all'

    @staticmethod
    def _get_pool_opt(pool_id, pool_name):
        ret = []
        if pool_id is not None:
            ret += _int_var('-poolId', pool_id)
        elif pool_name is not None:
            ret += _text_var('-poolName', pool_name)
        else:
            raise ValueError('either pool_id or pool_name '
                             'should be supplied.')
        return ret

    @staticmethod
    def _get_lun_opt(lun_id, lun_name, allow_empty=False):
        ret = []
        if lun_id is not None:
            ret += _int_var('-l', lun_id)
        elif lun_name is not None:
            ret += _text_var('-name', lun_name)
        elif not allow_empty:
            raise ValueError('either lun_id or lun_name '
                             'should be supplied.')
        return ret

    @staticmethod
    def _get_primary_lun_opt(primary_lun_id=None, primary_lun_name=None):
        ret = []
        if primary_lun_id is not None:
            ret += _int_var('-primaryLun', primary_lun_id)
        elif primary_lun_name is not None:
            ret += _text_var('-primaryLunName', primary_lun_name)
        else:
            raise ValueError('either primary lun name or '
                             'primary lun id should be supplied.')
        return ret

    @staticmethod
    def _get_provision_opt(provision):
        ret = []
        if provision is not None:
            possible_types = VNXProvisionEnum.get_all()
            if provision in possible_types:
                ret += VNXProvisionEnum.get_opt(provision)
            else:
                raise ValueError('not supported provisioning type: {}.'
                                 '  valid candidates: {}'
                                 .format(provision, possible_types))
        return ret

    @staticmethod
    def _get_tier_opt(tier):
        ret = []
        if tier is not None:
            possible_tiers = VNXTieringEnum.get_all()
            if tier in possible_tiers:
                ret += VNXTieringEnum.get_opt(tier)
            else:
                raise ValueError('not supported tiering type: {}.  '
                                 'valid candidates: {}'
                                 .format(tier, possible_tiers))
        return ret

    @command
    def create_pool_lun(self,
                        pool_name=None,
                        pool_id=None,
                        lun_name=None,
                        lun_id=None,
                        size=1,
                        provision=None,
                        tier=None):

        cmd = ['lun', '-create', '-capacity', size, '-sq', 'gb']
        cmd += self._get_pool_opt(pool_id, pool_name)
        cmd += self._get_lun_opt(lun_id, lun_name)
        cmd += self._get_provision_opt(provision)
        cmd += self._get_tier_opt(tier)
        return cmd

    @command
    def modify_lun(self,
                   lun_id=None,
                   lun_name=None,
                   new_name=None,
                   new_tier=None,
                   dedup=None):
        cmd = ['lun', '-modify']
        cmd += self._get_lun_opt(lun_id, lun_name)

        if new_name is not None:
            cmd += _text_var('-newName', new_name)

        cmd += self._get_tier_opt(new_tier)

        if dedup is not None:
            dedup_op = 'on' if dedup else 'off'
            cmd += ['-deduplication', dedup_op]

        cmd.append('-o')
        return cmd

    @command
    def enable_compression(self, lun_id=None, rate=None, pool_id=None,
                           pool_name=None, ignore_thresholds=False):
        cmd = ['compression', '-on']
        cmd += _int_var('-l', lun_id)
        if pool_id is not None:
            cmd += _int_var('-destPoolId', pool_id)
        elif pool_name is not None:
            cmd += _text_var('-destPoolName', pool_name)
        if rate is not None:
            cmd += _enum_var('-rate', rate, VNXCompressionRate)
        if ignore_thresholds:
            cmd.append('-ignoreThresholds')
        cmd.append('-o')
        return cmd

    @command
    def disable_compression(self, lun_id, ignore_thresholds=False):
        cmd = ['compression', '-off']
        cmd += _int_var('-l', lun_id)
        if ignore_thresholds:
            cmd.append('-ignoreThresholds')
        cmd.append('-o')
        return cmd

    @command
    def create_mount_point(self,
                           primary_lun_id=None,
                           primary_lun_name=None,
                           mount_point_name=None,
                           mount_point_id=None):
        cmd = 'lun -create -type snap'.split()
        cmd += self._get_primary_lun_opt(primary_lun_id, primary_lun_name)
        cmd += self._get_lun_opt(lun_id=mount_point_id,
                                 lun_name=mount_point_name)
        return cmd

    @command
    def attach_snap(self, snap_name, lun_id=None, lun_name=None):
        cmd = ['lun', '-attach']
        cmd += self._get_lun_opt(lun_id, lun_name)
        cmd += _text_var('-snapName', snap_name)
        return cmd

    @command
    def detach_snap(self, lun_id=None, lun_name=None):
        cmd = ['lun', '-detach']
        cmd += self._get_lun_opt(lun_id, lun_name)
        cmd.append('-o')
        return cmd

    @command
    def remove_pool_lun(self,
                        lun_id=None,
                        lun_name=None,
                        remove_snapshots=False,
                        force_detach=False):
        cmd = 'lun -destroy'.split()
        cmd += self._get_lun_opt(lun_id, lun_name)

        if remove_snapshots:
            cmd.append('-destroySnapshots')

        if force_detach:
            cmd.append('-forceDetach')

        cmd.append('-o')
        return cmd

    @command
    def expand_pool_lun(self, new_size, lun_id=None, lun_name=None,
                        ignore_thresholds=False):
        cmd = ['lun', '-expand']
        cmd += self._get_lun_opt(lun_id, lun_name)
        cmd += _int_var('-capacity', new_size)
        cmd += ['-sq', 'gb']
        if ignore_thresholds:
            cmd += ['-ignoreThresholds']
        cmd.append('-o')
        return cmd

    @command
    def migrate_lun(self, src_id, dst_id, rate=VNXMigrationRate.HIGH):
        cmd = ['migrate', '-start']
        cmd += _int_var('-source', src_id)
        cmd += _int_var('-dest', dst_id)
        cmd += _enum_var('-rate', rate, VNXMigrationRate)
        cmd.append('-o')
        return cmd

    @command
    def get_migration_session(self, src_id=None):
        cmd = ['migrate', '-list']
        if src_id is not None:
            cmd += _int_var('-source', src_id)
        return cmd

    @command
    def cancel_migrate_lun(self, src_id):
        if src_id is None:
            raise ValueError('source LUN id missing for cancel migration.')
        cmd = ['migrate', '-cancel']
        cmd += _int_var('-source', src_id)
        cmd.append('-o')
        return cmd

    @command
    def create_sg(self, name):
        cmd = ['storagegroup', '-create']
        cmd += _text_var('-gname', name)
        return cmd

    @command
    def sg_add_hlu(self, sg_name, hlu_id, alu_id):
        cmd = ['storagegroup', '-addhlu']
        cmd += _int_var('-hlu', hlu_id)
        cmd += _int_var('-alu', alu_id)
        cmd += _text_var('-gname', sg_name)
        cmd.append('-o')
        return cmd

    @command
    def sg_remove_hlu(self, sg_name, hlu_id):
        cmd = ['storagegroup', '-removehlu']
        cmd += _int_var('-hlu', hlu_id)
        cmd += _text_var('-gname', sg_name)
        cmd.append('-o')
        return cmd

    @staticmethod
    def _sg_host_op(sg_name, host_name, op):
        cmd = ['storagegroup', op]
        cmd += _text_var('-host', host_name)
        cmd += _text_var('-gname', sg_name)
        cmd.append('-o')
        return cmd

    @command
    def sg_connect_host(self, sg_name, host_name):
        return self._sg_host_op(sg_name, host_name, '-connecthost')

    @command
    def sg_disconnect_host(self, sg_name, host_name):
        return self._sg_host_op(sg_name, host_name, '-disconnecthost')

    @command
    def set_path(self, sg_name, hba_uid, sp, port_id,
                 ip, host, vport_id=None):

        cmd = ['storagegroup', '-setpath']
        cmd += _text_var('-gname', sg_name)
        cmd += _text_var('-hbauid', hba_uid)
        cmd += ['-sp', VNXSPEnum.get_sp_index(sp)]
        cmd += _int_var('-spport', port_id)
        if vport_id is not None:
            cmd += _int_var('-spvport', vport_id)
        cmd += ['-ip', ip]
        cmd += _text_var('-host', host)
        cmd.append('-o')
        return cmd

    @command
    def remove_hba(self, hba_uid):
        return ['port', '-removeHBA', '-hbauid', hba_uid, '-o']

    @command
    def remove_sg(self, sg_name):
        cmd = ['storagegroup', '-destroy']
        cmd += _text_var('-gname', sg_name)
        cmd.append('-o')
        return cmd

    @command
    def get_snap(self, name=None):
        cmd = ['snap', '-list']
        if name is not None:
            cmd += _text_var('-id', name)
        cmd.append('-detail')
        return cmd

    @staticmethod
    def _bool_to_yes_no(bool_value):
        if bool_value:
            ret = 'yes'
        else:
            ret = 'no'
        return ret

    @command
    def create_snap(self, res_id, snap_name,
                    allow_rw=True, auto_delete=False):
        cmd = ['snap', '-create']
        try:
            cmd += _int_var('-res', res_id)
        except ValueError:
            # string type meaning cg name
            cmd += _text_var('-res', res_id)
            cmd += ['-resType', 'CG']

        cmd += _text_var('-name', snap_name)
        if allow_rw is not None:
            cmd += ['-allowReadWrite', self._bool_to_yes_no(allow_rw)]
        if auto_delete is not None:
            cmd += ['-allowAutoDelete', self._bool_to_yes_no(auto_delete)]
        return cmd

    @command
    def copy_snap(self, src_name, tgt_name,
                  ignore_migration_check=False,
                  ignore_dedup_check=False):
        cmd = ['snap', '-copy']
        cmd += _text_var('-id', src_name)
        cmd += _text_var('-name', tgt_name)
        if ignore_migration_check:
            cmd.append('-ignoreMigrationCheck')
        if ignore_dedup_check:
            cmd.append('-ignoreDeduplicationCheck')
        return cmd

    @command
    def modify_snap(self, name, new_name=None, desc=None,
                    auto_delete=None, rw=None):
        opt = []
        if new_name is not None and name != new_name:
            opt += _text_var('-name', new_name)
        if desc is not None:
            opt += _text_var('-descr', desc)
        if auto_delete is not None:
            opt += ['-allowAutoDelete', self._bool_to_yes_no(auto_delete)]
        if rw is not None:
            opt += ['-allowReadWrite', self._bool_to_yes_no(rw)]
        if len(opt) > 0:
            cmd = ['snap', '-modify', '-id', name] + opt
        else:
            cmd = []
        return cmd

    @command
    def remove_snap(self, snap_name):
        cmd = ['snap', '-destroy']
        cmd += _text_var('-id', snap_name)
        cmd.append('-o')
        return cmd

    @staticmethod
    def _get_cg_member_repr(members):
        def member_converter(member):
            return six.text_type(check_int(member))

        return ','.join(map(member_converter, members))

    @command
    def create_cg(self, name, members=None, auto_delete=None):
        cmd = 'snap -group -create'.split()
        cmd += _text_var('-name', name)
        if auto_delete is not None:
            cmd += ['-allowSnapAutoDelete', self._bool_to_yes_no(auto_delete)]

        if members is not None and len(members) > 0:
            cmd += ['-res', self._get_cg_member_repr(members)]

        return cmd

    @classmethod
    def _cg_member_op(cls, name, op, members):
        if len(members) == 0:
            cmd = []
            log.warn('no member to add to cg: {}'.format(name))
        else:
            cmd = 'snap -group {} -id'.format(op).split()
            cmd.append(name)
            cmd += ['-res', cls._get_cg_member_repr(members)]
        return cmd

    @command
    def add_cg_member(self, name, *members):
        return self._cg_member_op(name, '-addmember', members)

    @command
    def remove_cg_member(self, name, *members):
        return self._cg_member_op(name, '-rmmember', members)

    @command
    def replace_cg_member(self, name, *members):
        return self._cg_member_op(name, '-replmember', members)

    @command
    def remove_cg(self, name):
        cmd = 'snap -group -destroy'.split()
        cmd += _text_var('-id', name)
        return cmd

    @command
    def get_ndu(self, name=None):
        cmd = 'ndu -list'.split()
        if name is not None:
            cmd += _text_var('-name', name)
        return cmd

    @property
    def ip(self):
        return self._heart_beat.get_alive_sp_ip()

    @retry(on_error=ex.VNXSPDownError)
    def execute(self, params, raise_on_rc=None, check_rc=False):
        if params is not None and len(params) > 0:
            ip = self.ip
            cmd = self._get_cmd_prefix(ip) + params
            output = self._heart_beat.execute_cmd(ip, cmd)
        else:
            log.info('no command to execute.  return empty.')
            output = ''
        return output
