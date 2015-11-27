# coding=utf-8
from __future__ import unicode_literals
import logging
from os.path import join, dirname, abspath, exists
import six
import vnxCliApi.cli

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)

_mock_data_dir = ('testdata', 'mock_output')


def read_test_file(name):
    p = dirname(abspath(__file__))
    p = join(p, *_mock_data_dir)
    p = join(p, name)
    ret = ''
    if not exists(p):
        log.warn('cannot find mock output file: %s, '
                 'default to empty string.', p)
    else:
        with open(p) as f:
            log.debug('read mock file: %s', p)
            ret = f.read()

    return ret


class MockCli(object):
    def __init__(self):
        self._output = None
        self._mock_map = None

    def mock_execute(self, params, **_):

        if self._output is not None:
            filename = self._output
        else:
            filename = '{}.txt'.format(self.get_filename(params))
        return read_test_file(filename)

    @staticmethod
    def get_filename(params):
        def remove_flag(arr, flag, flag_length=1):
            if flag in arr:
                i = arr.index(flag)
                if i > 0:
                    arr = arr[0:i] + arr[i + flag_length:]
                else:
                    arr = arr[flag_length:]
            return arr

        def remove_cli_binary(p):
            return p[1:]

        params = remove_cli_binary(params)

        flags_to_remove = {
            '-np': 1,
            '-t': 2,
            '-user': 2,
            '-password': 2,
            '-scope': 2,
            '-h': 2
        }

        for k, v in six.iteritems(flags_to_remove):
            params = remove_flag(params, k, v)
        return '_'.join(map(six.text_type, params))

    def update_mock_output(self, output, mock_map):
        self._output = output
        self._mock_map = mock_map


def patch_cli(output=None, mock_map=None):
    cli = MockCli()

    def decorator(func):
        def func_wrapper(self):
            orig = vnxCliApi.cli.NaviCommand.execute
            ret = vnxCliApi.cli.NaviCommand.execute = cli.mock_execute

            cli.update_mock_output(output, mock_map)
            func(self)

            if orig:
                vnxCliApi.cli.NaviCommand.execute = orig

            return ret

        return func_wrapper

    return decorator


def extract_command(func):
    """patch `CliClient.execute` method for unittest

    Patch `CliClient.execute` to return the parameters.
    The command line parameter can be verified by unittest.

    :param func: test function to wrap
    """

    def mock(_, commands):
        return ' '.join(map(six.text_type, commands))

    def func_wrapper(self):
        orig = vnxCliApi.cli.CliClient.execute
        vnxCliApi.cli.CliClient.execute = mock

        ret = func(self)

        if orig:
            vnxCliApi.cli.CliClient.execute = orig
        return ret

    return func_wrapper
