# coding=utf-8
from __future__ import unicode_literals

import logging
import os

import six
from subprocess import Popen, PIPE

from vnxCliApi.exception import NaviseccliNotAvailableError
from vnxCliApi.lib.common import int_var, text_var, synchronized, cache

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class NaviCommand(object):
    def __init__(self, username=None, password=None, scope=0,
                 sec_file=None, timeout=None):
        self._username = username
        self._password = password
        self._scope = scope
        self._sec_file = sec_file
        self._timeout = timeout

        self._init_security_level()

    MAX_TIMEOUT = 1800
    MIN_TIMEOUT = 3

    @property
    def timeout(self):
        ret = self._timeout
        if ret is not None:
            ret = int(ret)
            if ret > 1800:
                log.warning('timeout {0} is larger than {1}, reset to {1}.'
                            .format(ret, self.MAX_TIMEOUT))
                ret = 1800
            if ret < 3:
                log.warning('timeout {0} is less than {1}, reset to {1}.'
                            .format(ret, self.MIN_TIMEOUT))
                ret = 3
        return ret

    def get_credentials(self):
        if self._username is None and self._password is None:
            # use security file
            if self._sec_file is not None:
                ret = text_var('-secfilepath', self._sec_file)
            else:
                ret = []
        elif self._username is None or self._password is None:
            raise ValueError('username or password missing.')
        else:
            ret = ['-user', self._username,
                   '-password', self._password,
                   '-scope', self._scope]
        if self.timeout is not None:
            ret += int_var('-t', self.timeout)
        return ret

    _cli_binary_candidates = (
        r'/opt/Navisphere/bin/naviseccli',
        r'C:\Program Files (x86)\EMC\Navisphere CLI\naviseccli.exe',
        r'C:\Program Files\EMC\Navisphere CLI\naviseccli.exe')

    @classmethod
    @cache()
    def _binary(cls):
        binary = 'naviseccli'
        for c in cls._cli_binary_candidates:
            if os.path.exists(c):
                binary = c
                break
        return binary

    def _get_cmd_prefix(self, ip):
        binary = self._binary()
        return [binary, '-h', ip] + self.get_credentials()

    @staticmethod
    def execute_naviseccli(cmd, raise_on_rc=None, check_rc=False):
        cmd = list(map(six.text_type, cmd))
        cmd_str = ' '.join(cmd)
        log.debug('call command: %s', cmd_str)
        try:
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        except WindowsError:
            raise NaviseccliNotAvailableError()
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

    @classmethod
    def get_security_level(cls):
        cmd = 'security -certificate -getLevel'.split()
        cmd.insert(0, cls._binary())
        return cls.execute_naviseccli(cmd).lower()

    @classmethod
    def set_security_level(cls, level='low'):
        possible_security_level = ('low', 'high')
        if level not in possible_security_level:
            raise ValueError(
                'possible security level: {}'.format(
                    possible_security_level))
        cmd = 'security -certificate -setLevel {}'.format(level).split()
        cmd.insert(0, cls._binary())
        cls.execute_naviseccli(cmd)

    @staticmethod
    @synchronized()
    @cache()
    def _init_security_level():
        # have to specify the specified class
        # otherwise cls could be different for different subclass
        # and cache won't work.
        cls = NaviCommand
        current_level = cls.get_security_level()
        if current_level != 'low':
            log.warn('security level is "{}", update to "low".'.format(
                current_level))
            cls.set_security_level('low')
