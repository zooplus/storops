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

import functools
import paramiko
from pywbemReq import WBEMConnection
from paramiko import ssh_exception
import six
from storops.connection import client
from storops.connection.exceptions import SFtpExecutionError, \
    SSHExecutionError, HTTPClientError
from retryz import retry

LOG = logging.getLogger(__name__)


def require_csrf_token(func):
    @functools.wraps(func)
    def decorator(self, url, **kwargs):
        wrapped = retry(on_error=self._http_authentication_error,
                        on_retry=self._update_csrf_token)(func)
        return wrapped(self, url, **kwargs)

    return decorator


class UnityRESTConnector(object):
    HEADERS = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Accept_Language': 'en_US',
        'Visibility': 'Engineering',
        'X-EMC-REST-CLIENT': 'true',
        'User-agent': 'EMC-OpenStack',
    }

    def __init__(self, host, port=443, user='admin', password=''):
        base_url = 'https://{host}:{port}'.format(host=host, port=port)

        self.http_client = client.HTTPClient(base_url=base_url,
                                             headers=self.HEADERS,
                                             auth=(user, password),
                                             insecure=True)

    def get(self, url, **kwargs):
        return self.http_client.get(url, **kwargs)

    @staticmethod
    def _http_authentication_error(err):
        return isinstance(err, HTTPClientError) and err.http_status == 401

    @require_csrf_token
    def post(self, url, **kwargs):
        return self.http_client.post(url, **kwargs)

    @require_csrf_token
    def delete(self, url, **kwargs):
        return self.http_client.delete(url, **kwargs)

    def _update_csrf_token(self):
        path_user = '/api/types/user/instances'
        resp, body = self.get(path_user)
        headers = {'emc-csrf-token': resp.headers['emc-csrf-token']}
        self.http_client.update_headers(headers)


class UnityWbemConnector(object):
    ns = 'root/emc/smis'

    def __init__(self, host, user, password, namespace=None):
        if namespace is None:
            namespace = 'interop'
        if user is not None and '/' not in user:
            user = 'Local/{}'.format(user)
        if host is not None and 'https' not in host:
            host = 'https://{}:5989'.format(host)
        self.conn = WBEMConnection(host, (user, password), namespace)

    def ei(self, clz_name):
        """ enumerate instance

        :param clz_name: CIM class name
        :return: instances of the class
        """
        return self.conn.EnumerateInstances(clz_name, self.ns)

    def gi(self, obj_name):
        """ get instance

        :param obj_name: instance name
        :return: instance
        """
        return self.conn.GetInstance(obj_name)

    def im(self, method_name, instance_name, **kwargs):
        """ invoke method

        :param method_name: method name
        :param instance_name: instance name
        :param kwargs: method parameters
        :return: method return
        """
        return self.conn.InvokeMethod(
            method_name, instance_name, kwargs.items())

    def ai(self, from_inst_name, assoc_clz, result_clz):
        """ associators

        :param from_inst_name: from instance
        :param assoc_clz: the associate class
        :param result_clz: the result class
        :return: associated instances
        """
        return self.conn.Associators(from_inst_name,
                                     AssocClass=assoc_clz,
                                     ResultClass=result_clz)

    def ei_first(self, clz_name):
        """ enumerate first.

        :param clz_name: class to enumerate
        :return: first instance of the enumerate result
        """
        instances = self.ei(clz_name)
        if len(instances) > 0:
            ret = instances[0]
        else:
            raise ValueError('instance of "{}" not found.'.format(clz_name))
        return ret

    def ref(self, obj_name, result_clz):
        """ reference

        :param obj_name: instance name
        :param result_clz: result class name
        :return: result instances
        """
        return self.conn.References(obj_name, ResultClass=result_clz)

    def di(self, obj_name):
        """ delete instance

        :param obj_name: instance name
        :return: operation result
        """
        return self.conn.DeleteInstance(obj_name)


class XMLAPIConnector(object):
    HEADERS = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(self, host, user='nasadim', password=''):
        base_url = 'https://{}'.format(host)

        self.http_client = client.HTTPClient(base_url=base_url,
                                             headers=self.HEADERS,
                                             auth=(user, password),
                                             insecure=True)

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

    def copy_file_to_remote(self, local_path, remote_path):
        """scp the local file to remote folder.

        :param local_path: local path
        :param remote_path: remote path
        """
        sftp_client = self.transport.open_sftp_client()
        LOG.debug('Copy the local file to remote. '
                  'Source=%(src)s. Target=%(target)s.' %
                  {'src': local_path, 'target': remote_path})
        try:
            sftp_client.put(local_path, remote_path)
        except Exception as ex:
            LOG.error('Failed to copy the local file to remote. '
                      'Reason: %s.' % six.text_type(ex))
            raise SFtpExecutionError(err=ex)

    def get_remote_file(self, remote_path, local_path):
        """Fetch remote File.

        :param remote_path: remote path
        :param local_path: local path
        """
        sftp_client = self.transport.open_sftp_client()
        LOG.debug('Get the remote file. '
                  'Source=%(src)s. Target=%(target)s.' %
                  {'src': remote_path, 'target': local_path})
        try:
            sftp_client.get(remote_path, local_path)
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
