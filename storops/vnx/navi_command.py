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

import logging
import os

import six
from subprocess import Popen, PIPE

import time

from storops.exception import NaviseccliNotAvailableError
from storops.lib.common import int_var, text_var, synchronized, cache

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class NaviCommand(object):
    def __init__(self, username=None, password=None, scope=0,
                 sec_file=None, timeout=None, naviseccli=None):
        self._username = username
        self._password = password
        self._scope = scope
        self._sec_file = sec_file
        self._timeout = timeout
        self._customized_cli = naviseccli

    MAX_TIMEOUT = 1800
    MIN_TIMEOUT = 3

    def set_credential(self, username=None, password=None, scope=None,
                       sec_file=None):
        if username is not None:
            self._username = username
        if password is not None:
            self._password = password
        if scope is not None:
            self._scope = scope
        if sec_file is not None:
            self._sec_file = sec_file

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

    def set_binary(self, binary):
        """ set the location of naviseccli binary

        :param binary: the absolute path of naviseccli
        :return: nothing
        """
        self._customized_cli = binary

    def _binary(self):
        if self._customized_cli is None:
            binary = 'naviseccli'
            for c in self._cli_binary_candidates:
                if os.path.exists(c):
                    binary = c
                    break
        else:
            binary = self._customized_cli
        self._init_security_level(binary)
        return binary

    def get_cmd_prefix(self, ip):
        binary = self._binary()
        return [binary, '-h', ip] + self.get_credentials()

    @classmethod
    def execute_naviseccli(cls, cmd,
                           raise_on_rc=None, check_rc=False):
        def _log_command():
            cmd_str = ' '.join(cmd)
            log.debug('call command: {}'.format(cmd_str))

        cmd = list(map(six.text_type, cmd))
        _log_command()
        start = time.time()
        try:
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        except OSError:
            raise NaviseccliNotAvailableError()
        output = p.stdout.read()
        p.wait()
        rc = p.returncode
        log.debug('time consumed (s): {}\n'
                  'return code: {}\n'
                  'output:\n{}'.format(time.time() - start, rc, output))
        if rc is not None:
            if rc == raise_on_rc or (check_rc and rc != 0):
                raise ValueError('raise error on return code "{}".'
                                 .format(rc))
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        return output.strip()

    @classmethod
    def get_security_level(cls, binary):
        cmd = 'security -certificate -getLevel'.split()
        cmd.insert(0, binary)
        return cls.execute_naviseccli(cmd).lower()

    @classmethod
    def set_security_level(cls, binary, level='low'):
        possible_security_level = ('low', 'high')
        if level not in possible_security_level:
            raise ValueError(
                'possible security level: {}'.format(
                    possible_security_level))
        cmd = 'security -certificate -setLevel {}'.format(level).split()
        cmd.insert(0, binary)
        cls.execute_naviseccli(cmd)

    @staticmethod
    @synchronized()
    @cache()
    def _init_security_level(binary):
        # have to specify the specified class
        # otherwise cls could be different for different subclass
        # and cache won't work.
        cls = NaviCommand
        current_level = cls.get_security_level(binary)
        if current_level != 'low':
            log.warn('security level is "{}", update to "low".'.format(
                current_level))
            cls.set_security_level(binary, 'low')
