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
import pipes

import paramiko
from paramiko import ssh_exception
import six
from vnxCliApi.connection import client
from vnxCliApi.connection.exceptions import SFtpExecutionError, \
    SSHExecutionError, HTTPClientError

LOG = logging.getLogger(__name__)


class VNXeRESTConnector(object):
    HEADERS = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Accept_Language': 'en_US',
        'Visibility': 'Engineering',
        'X-EMC-REST-CLIENT': 'true',
        'User-agent': 'EMC-OpenStack',
    }

    def __init__(self, host, port=443, user='admin', password='', debug=False):
        base_url = 'https://{host}:{port}'.format(host=host, port=port)

        self.http_client = client.HTTPClient(base_url=base_url,
                                             headers=self.HEADERS,
                                             auth=(user, password),
                                             insecure=True,
                                             http_log_debug=debug)
        self.csrf_token = None

    def get(self, url, **kwargs):
        return self.http_client.get(url, **kwargs)

    def post(self, url, **kwargs):
        try:
            self.http_client.post(url, **kwargs)
        except HTTPClientError as ex:
            if ex.http_status == 401:
                if self.csrf_token is None:
                    self._update_csrf_token()
                headers = {'emc-csrf-token': self.csrf_token}
                self.http_client.update_headers(headers)
                self.http_client.post(url, **kwargs)
            else:
                raise

    def delete(self, url, **kwargs):
        try:
            self.http_client.delete(url, **kwargs)
        except HTTPClientError as ex:
            if ex.http_status == 401:
                if self.csrf_token is None:
                    self._update_csrf_token()
                headers = {'emc-csrf-token': self.csrf_token}
                self.http_client.update_headers(headers)
                self.http_client.delete(url, **kwargs)
            else:
                raise

    def _update_csrf_token(self):
        path_user = '/api/types/user/instances'
        resp, body = self.get(path_user)
        self.csrf_token = resp.headers['emc-csrf-token']


class XMLAPIConnector(object):
    HEADERS = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(self, host, user='nasadim', password='', debug=False):
        base_url = 'https://{}'.format(host)

        self.http_client = client.HTTPClient(base_url=base_url,
                                             headers=self.HEADERS,
                                             auth=(user, password),
                                             insecure=True,
                                             http_log_debug=debug)

        self.host = host
        self.user = user
        self.password = password

        self._login(host, user, password)

    def _login(self, host, user, password):
        url = 'https://{}/Login/?user={}&password={}&Login=Login'.format(
            host, user, password)

        self.http_client.request(url, 'GET')

    def post(self, body):
        url = '/servlets/CelerraManagementServices'
        try:
            return self.http_client.post(url, body=body)
        except HTTPClientError as ex:
            if ex.http_status == 403:
                self._login(self.host, self.user, self.password)
                self.http_client.post(url, body=body)
            else:
                raise


class SSHConnector(object):
    """SSH Connection to the specified host."""

    def __init__(self, host, username, password, port=22):
        self.transport = None
        self.init_connection(host, password, port, username)
        self.isLive = True

    def init_connection(self, host, password, port, username):
        self.transport = paramiko.Transport((host, port))
        # Currently we only support to use the password to ssh.
        if password:
            try:
                self.transport.connect(username=username, password=password)
            except ssh_exception.SSHException as ex:
                error_msg = ('Failed to setup SSH connection. '
                             'Reason:%s.' % six.text_type(ex))
                LOG.error(error_msg)
                raise ex

    def execute(self, command, timeout=None, check_exit_code=True):
        """Executes the given command on the remote host."""
        cmd = ' '.join(pipes.quote(cmd_arg) for cmd_arg in command)
        channel = self.transport.open_session()
        channel.exec_command(cmd)
        channel.settimeout(timeout)
        exit_status = channel.recv_exit_status()

        stdout = channel.makefile('r').read()
        stderr = channel.makefile_stderr('r').read()

        channel.makefile('wb').close()
        self._ssh_command_log(cmd, stdout, stderr)

        # exit_status == -1 if no exit code was returned
        if exit_status != -1:
            LOG.debug('Result was %s' % exit_status)
            if check_exit_code and exit_status != 0:
                raise SSHExecutionError(exit_code=exit_status,
                                        stdout=stdout,
                                        stderr=stderr,
                                        cmd=cmd)

        return stdout, stderr

    def copy_file_to_remote(self, localpath, remotepath):
        """scp the local file to remote folder."""
        sftp_client = self.transport.open_sftp_client()
        LOG.debug('Copy the local file to remote. '
                  'Source=%(src)s. Target=%(target)s.' %
                  {'src': localpath, 'target': remotepath})
        try:
            sftp_client.put(localpath, remotepath)
        except Exception as ex:
            LOG.error('Failed to copy the local file to remote. '
                      'Reason: %s.' % six.text_type(ex))
            raise SFtpExecutionError(err=ex)

    def get_remote_file(self, remotepath, localpath):
        """Fetch remote File."""
        sftp_client = self.transport.open_sftp_client()
        LOG.debug('Get the remote file. '
                  'Source=%(src)s. Target=%(target)s.' %
                  {'src': remotepath, 'target': localpath})
        try:
            sftp_client.get(remotepath, localpath)
        except Exception as ex:
            LOG.error('Failed to secure copy. Reason: %s.' %
                      six.text_type(ex))
            raise SFtpExecutionError(err=ex)

    def close(self):
        """Closes the ssh connection."""
        if 'isLive' in self.__dict__ and self.isLive:
            self.transport.close()
            self.isLive = False

    def __del__(self):
        """Try to close the ssh connection if not explicitly closed."""
        self.close()

    @staticmethod
    def _ssh_command_log(command, stdout, stderr):
        LOG.debug('[SSH Command] {}\n'
                  '[stdout] {}\n'
                  '[stderr] {}\n'
                  .format(command, stdout, stderr))
