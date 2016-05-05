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

import functools
import logging
import os

import re
from mock import patch
from test.utils import ConnectorMock

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class MockCimConnection(ConnectorMock):
    base_folder = os.path.join('unity', 'cim_data')

    clz_name_pattern = re.compile(r'<CLASSNAME NAME="(\w+)"/>')
    inst_clz_name_pattern = re.compile(r'CLASSNAME="(\w+)">')
    result_clz_pattern = re.compile(
        r'<IPARAMVALUE NAME="ResultClass"><CLASSNAME NAME="(\w+)"/>')
    assoc_clz_pattern = re.compile(
        r'<IPARAMVALUE NAME="AssocClass"><CLASSNAME NAME="(\w+)"/>')
    method_name_pattern = re.compile(r'<METHODCALL NAME="(\w+)">')

    @classmethod
    def get_folder(cls, inputs):
        url, req = inputs
        sub_folder = cls._get_method_sub_folder(req)
        return os.path.join(cls.base_folder, sub_folder)

    @classmethod
    def _get_matched(cls, pattern, req):
        matched = re.findall(pattern, req)
        if matched:
            ret = matched[0]
        else:
            ret = None
        return ret

    @classmethod
    def _get_assoc_file_name(cls, req):
        result_clz = cls._get_matched(cls.result_clz_pattern, req)
        assoc_clz = cls._get_matched(cls.assoc_clz_pattern, req)
        src_clz = cls._get_matched(cls.inst_clz_name_pattern, req)
        return '{}-{}-{}'.format(src_clz, assoc_clz, result_clz)

    @classmethod
    def _get_ref_file_name(cls, req):
        result_clz = cls._get_matched(cls.clz_name_pattern, req)
        obj_clz = cls._get_matched(cls.inst_clz_name_pattern, req)
        return '{}-{}'.format(obj_clz, result_clz)

    @classmethod
    def get_filename(cls, inputs):
        url, req = inputs
        ret = None
        if cls._is_enumerate_instance(req):
            ret = cls._get_matched(cls.clz_name_pattern, req)
        elif cls._is_method_call(req):
            ret = cls._get_matched(cls.method_name_pattern, req)
        elif cls._is_associate(req):
            ret = cls._get_assoc_file_name(req)
        elif cls._is_reference(req):
            ret = cls._get_ref_file_name(req)
        elif cls._is_delete_instance(req):
            ret = cls._get_matched(cls.inst_clz_name_pattern, req)
        elif cls._is_get_instance(req):
            ret = cls._get_matched(cls.inst_clz_name_pattern, req)

        if ret is None:
            raise ValueError('mock output not found.  req: \n{}'.format(req))
        else:
            ret = '{}.xml'.format(ret)
        return ret

    @classmethod
    def _get_method_sub_folder(cls, req):
        if cls._is_method_call(req):
            ret = 'method_call'
        elif cls._is_enumerate_instance(req):
            ret = 'enumerate_instance'
        elif cls._is_associate(req):
            ret = 'associate'
        elif cls._is_get_instance(req):
            ret = 'get_instance'
        elif cls._is_register_observer(req):
            ret = 'register_observer'
        elif cls._is_deregister_observer(req):
            ret = 'deregister_observer'
        elif cls._is_reference(req):
            ret = 'reference'
        elif cls._is_delete_instance(req):
            ret = 'delete_instance'
        else:
            raise ValueError(
                'mock output sub folder for {} not found.'.format(req))
        return ret

    @classmethod
    def _is_enumerate_instance(cls, request):
        return cls._i_method_call_node('EnumerateInstances') in request

    @classmethod
    def _is_associate(cls, request):
        return cls._i_method_call_node('Associators') in request

    @classmethod
    def _is_get_instance(cls, request):
        return cls._i_method_call_node('GetInstance') in request

    @classmethod
    def _is_reference(cls, request):
        return cls._i_method_call_node('References') in request

    @classmethod
    def _is_delete_instance(cls, request):
        return cls._i_method_call_node('DeleteInstance') in request

    @classmethod
    def _is_register_observer(cls, request):
        return cls._i_method_call_node('registerobserver') in request

    @classmethod
    def _is_deregister_observer(cls, request):
        return cls._i_method_call_node('deregisterobserver') in request

    @classmethod
    def _is_method_call(cls, request):
        return '<METHODCALL NAME="' in request

    @classmethod
    def _param_assoc_clz(cls, clz_name):
        return cls._i_param_value_node('AssocClass').format(clz_name)

    @classmethod
    def _param_result_clz(cls, clz_name):
        return cls._i_param_value_node('ResultClass').format(clz_name)

    @classmethod
    def _method_call_node(cls, name):
        return '<METHODCALL NAME="{}">'.format(name)

    @classmethod
    def _i_param_value_node(cls, name):
        return ('<IPARAMVALUE NAME="{}">'
                '<CLASSNAME NAME="{{}}"/></IPARAMVALUE>'
                .format(name))

    @classmethod
    def _i_method_call_node(cls, name):
        return '<IMETHODCALL NAME="{}">'.format(name)

    @classmethod
    def _class_name_node(cls, name):
        return '<CLASSNAME NAME="{}"/>'.format(name)

    @classmethod
    def _instance_name_node(cls, clz_name, key_name, key_value):
        return ('<INSTANCENAME CLASSNAME="{}">'
                '<KEYBINDING NAME="{}">'
                '<KEYVALUE VALUETYPE="string">{}</KEYVALUE>'
                '</KEYBINDING>'
                '</INSTANCENAME>'.format(clz_name, key_name, key_value))

    def mock_request(self, url, data, creds, headers=None, ca_certs=None,
                     verify=False, timeout=None, *args, **kwargs):

        req = ("<mock request {{"
               "url: {}, "
               "creds: {}, "
               "headers: {}, "
               "ca_certs: {}, "
               "verify: {}, "
               "timeout: {},"
               "args: {},"
               "kwargs: {}}}"
               .format(url,
                       creds,
                       headers,
                       ca_certs,
                       verify,
                       timeout,
                       args,
                       kwargs))
        log.debug(req)
        log.debug('request data: \n{}'.format(data))
        return self.get_mock_output([url, data])


def patch_cim(output=None, mock_map=None):
    conn = MockCimConnection(output=output, mock_map=mock_map)

    def decorator(func):
        @functools.wraps(func)
        @patch(target='pywbemReq.cim_http.wbem_request',
               new=conn.mock_request)
        def func_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return func_wrapper

    return decorator
