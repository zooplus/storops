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

import copy
import json
import logging

import requests
from requests.exceptions import RequestException
from retryz import retry

from storops.connection.exceptions import ClientException, BadRequest, \
    from_response
from storops.connection.lib import strutils


class HTTPClient(object):
    def __init__(self, base_url, headers, insecure=False, auth=None,
                 timeout=None, retries=None,
                 http_log_debug=True):
        self.base_url = base_url
        if retries is None:
            retries = float('inf')
        self.retries = retries
        self.http_log_debug = http_log_debug

        self.request_options = self._set_request_options(
            insecure, auth, timeout)

        self.headers = headers

        self.session = requests.session()

        self._logger = logging.getLogger(__name__)
        if self.http_log_debug:
            ch = logging.StreamHandler()
            self._logger.setLevel(logging.ERROR)
            self._logger.addHandler(ch)
            if hasattr(requests, 'logging'):
                requests.logging.getLogger(requests.__name__).addHandler(ch)

    def __del__(self):
        self.session.close()

    @staticmethod
    def _set_request_options(insecure=None, auth=None, timeout=None):
        options = {'verify': True}

        if insecure:
            options['verify'] = False

        if timeout:
            options['timeout'] = timeout

        options['auth'] = auth

        return options

    def request(self, full_url, method, **kwargs):
        headers = copy.deepcopy(self.headers)
        headers.update(kwargs.get('headers', {}))

        options = copy.deepcopy(self.request_options)

        if 'body' in kwargs:
            if headers['Content-Type'] == 'application/json':
                options['data'] = json.dumps(kwargs['body'])
            else:
                options['data'] = kwargs['body']

        self.log_request(method, full_url, headers, options.get('data', None))
        resp = self.session.request(method, full_url, headers=headers,
                                    **options)

        self.log_response(resp)

        body = None
        if resp.text:
            try:
                if headers['Content-Type'] == 'application/json':
                    body = json.loads(resp.text)
                else:
                    body = resp.text

            except ValueError:
                pass

        if resp.status_code >= 400:
            raise from_response(resp, method, full_url)

        return resp, body

    def _cs_request(self, url, method, **kwargs):
        return self._cs_request_with_retries(
            self.base_url + url,
            method,
            **kwargs)

    @staticmethod
    def _wait_callback(tried):
        return 2 ** (tried - 1)

    def _get_limit(self):
        return self.retries

    @retry(wait=lambda x: 2 ** (x - 1), limit=_get_limit,
           on_error=lambda e: isinstance(e, (
               BadRequest, RequestException, ClientException)))
    def _cs_request_with_retries(self, url, method, **kwargs):
        return self.request(url, method, **kwargs)

    def get(self, url, **kwargs):
        return self._cs_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self._cs_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        return self._cs_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        return self._cs_request(url, 'DELETE', **kwargs)

    def log_request(self, method, url, headers, data=None):
        if not self.http_log_debug:
            return

        string_parts = ['curl -i', ' -X %s' % method, ' %s' % url]

        for element in headers:
            header = ' -H "%s: %s"' % (element, headers[element])
            string_parts.append(header)

        if data:
            if "password" in data:
                data = strutils.mask_password(data)
            string_parts.append(" -d '%s'" % data)
        self._logger.debug("\nREQ: %s\n" % "".join(string_parts))

    def log_response(self, resp):
        if not self.http_log_debug:
            return
        self._logger.debug(
            "RESP: [%(code)s] %(headers)s\nRESP BODY: %(body)s\n" % {
                'code': resp.status_code,
                'headers': resp.headers,
                'body': resp.text
            })

    def update_headers(self, headers):
        self.headers.update(headers)
