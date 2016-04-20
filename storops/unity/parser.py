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

from storops.lib.common import cache
from storops.lib.parser import ParserConfigFactory, OutputParser

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class UnityParserConfigFactory(ParserConfigFactory):
    @classmethod
    def get_parser_clz(cls, data_src):
        if data_src is None or data_src == 'rest':
            ret = UnityRestParser
        else:
            raise ValueError('data_src {} not supported.'.format(data_src))
        return ret


_factory_singleton = UnityParserConfigFactory()


@cache
def get_unity_parser(name):
    return _factory_singleton.get(name)


class UnityRestParser(OutputParser):
    data_src = 'rest'

    def __init__(self):
        super(UnityRestParser, self).__init__()
        self.name = None

    def parse_all(self, output, properties=None):
        try:
            output = output.contents
        except AttributeError:
            pass
        return output

    def parse(self, output, properties=None):
        try:
            output = output.first_content
        except AttributeError:
            pass
        return self._parse_object(output)

    def _parse_object(self, obj, properties=None):
        if properties is None:
            properties = self.properties

        ret = {}
        for p in properties:
            if isinstance(obj, list):
                log.error('cannot parse list: {}.  '
                          'a list converter must be specified.'.format(obj))
                continue
            if p.label in obj.keys():
                value = p.convert(obj[p.label])
                ret[p.key] = value
        return ret

    def init_from_config(self, config):
        self.name = config.name
