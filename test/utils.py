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

import codecs
import logging

from os.path import dirname, abspath, join, exists, basename

__author__ = 'Jay Xu'

log = logging.getLogger(__name__)


def read_test_file(folder, name):
    p = dirname(abspath(__file__))
    p = join(p, folder)
    p = join(p, name)
    if not exists(p):
        log.warn('cannot find mock output file: %s, '
                 'default to empty string.', p)
        raise IOError('file: {} not found.'.format(p))
    else:
        with codecs.open(p, 'r', 'utf-8') as f:
            if basename(p) not in ('index.xml', 'index.json'):
                log.debug('read mock file: %s', p)
            ret = f.read()

    return ret


class ConnectorMock(object):
    base_folder = ''

    def __init__(self, output=None, mock_map=None):
        self._output = output
        self._mock_map = mock_map

    @classmethod
    def read_file(cls, filename, *sub_folders):
        folder = join(cls.base_folder, *sub_folders)
        return read_test_file(folder, filename)

    def update_mock_output(self, output, mock_map):
        self._output = output
        self._mock_map = mock_map

    def get_file_in_mock_map(self, param):
        ret = None
        if self._mock_map is not None:
            for key in self._mock_map.keys():
                if param.startswith(key):
                    ret = self._mock_map[key]
                    break
        return ret

    def get_mock_output(self, inputs):
        filename = self.get_filename(inputs)
        folder = self.get_folder(inputs)
        from_map = self.get_file_in_mock_map(filename)
        if self._output is not None:
            filename = self._output
        elif from_map:
            filename = from_map

        return read_test_file(folder, filename)

    def get_filename(self, inputs):
        raise NotImplementedError('specify the inputs-filename mapping.')

    def get_folder(self, inputs):
        raise NotImplementedError('mock data folder not specified.')
