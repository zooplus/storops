# coding=utf-8
from __future__ import unicode_literals

import logging
import re

from lxml import etree as ET
from retryz import retry

from vnxCliApi.connection.exceptions import SSHExecutionError
from vnxCliApi.exception import VNXLockRequiredException
from vnxCliApi.vnx import constants as const
from vnxCliApi.vnx.parsers import get_parser_config

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class Resource(object):
    """Base class for Storage resources.

    This is pretty much just a bag for attributes.
    """

    def __init__(self, manager, info=None, loaded=False):
        """Populate and bind to a manager.

        :param manager: BaseManager object
        :param info: dictionary representing resource attributes
        :param loaded: prevent lazy-loading if set to True
        """
        if info is None:
            info = {}
        self.manager = manager
        self._info = info
        self._add_details(info)
        self._loaded = loaded

    def __repr__(self):
        reprkeys = sorted(k
                          for k in self.__dict__.keys()
                          if k[0] != '_' and k != 'manager')

        info = ", ".join("%s=%s" % (k, getattr(self, k)) for k in reprkeys)
        return "<%s %s>" % (self.__class__.__name__, info)

    @classmethod
    def _get_parser(cls):
        return get_parser_config(cls.__name__)

    def _add_details(self, info):
        for prop_desc in self._get_parser().get_all_property_descriptor():
            try:
                if prop_desc.label in info:
                    setattr(self, prop_desc.key, info[prop_desc.label])
                    self._info[prop_desc.label] = info[prop_desc.label]
            except AttributeError:
                # In this case we already defined the attribute on the class
                pass

    def __getattr__(self, k):
        if k not in self.__dict__:
            # Disallow lazy-loading if already loaded once
            if not self.is_loaded():
                self.get()
                return self.__getattr__(k)

            raise AttributeError(k)
        else:
            return self.__dict__[k]

    def get(self):
        """Support for lazy loading details."""
        if hasattr(self.manager, 'get_resource'):
            new = self.manager.get_resource(self)
            if new:
                self._add_details(new._info)

        # self.manager.get may check lazy loaded status, so the status
        # setting should be after the function self.manager.get.
        self.set_loaded(True)

    def __eq__(self, other):
        if not isinstance(other, Resource):
            return NotImplemented
        # two resources of different types are not equal
        if not isinstance(other, self.__class__):
            return False
        return self._info == other._info

    def is_loaded(self):
        return self._loaded

    def set_loaded(self, val):
        self._loaded = val

    def update(self, data=None):
        # Update resource with the input information or the one retrieved
        # from the array.
        if data:
            self._add_details(data)
            self.set_loaded(True)
        else:
            self.set_loaded(False)
            self.get()


class ResourceManager(object):
    def __init__(self, manager):
        self.manager = manager
        self.xml_connector = manager.xml['connector']
        self.xml_parser = manager.xml['parser']
        self.xml_builder = manager.xml['builder']

        self.ssh_connector = manager.ssh['connector']

        self.retry_patterns = [
            (
                const.DEFAULT_RETRY_PATTERN,
                VNXLockRequiredException()
            ),
        ]

    def get_resource(self, resource):
        """Update the resource information.

        Re-implement this function in the subclass if more input parameters
        besides resource name are necessary in manager.get().
        :param resource: """
        if hasattr(self, 'get'):
            return self.get(resource.name)

    @staticmethod
    def _cache_missed(name, cache):
        return name not in cache or not cache[name].is_loaded()

    def _build_query_package(self, body):
        return self.xml_builder.RequestPacket(
            self.xml_builder.Request(
                self.xml_builder.Query(body)
            )
        )

    def _build_task_package(self, body):
        return self.xml_builder.RequestPacket(
            self.xml_builder.Request(
                self.xml_builder.StartTask(body, timeout='300')
            )
        )

    @retry(on_error=VNXLockRequiredException)
    def _send_request(self, req, retry_patterns=None):

        req_xml = const.XML_HEADER + ET.tostring(req).decode('utf-8')

        rsp_xml = self.xml_connector.post(str(req_xml))
        if isinstance(rsp_xml, tuple):
            rsp_xml = rsp_xml[1]

        response = self.xml_parser.parse(rsp_xml)

        self._translate_response(response)

        if not retry_patterns:
            retry_patterns = self.retry_patterns
        if response['maxSeverity'] == const.STATUS_ERROR:
            for pattern in retry_patterns:
                messages = self._get_problem_messages(response['problems'])
                for msg in messages:
                    if re.search(pattern[0], msg):
                        raise pattern[1]

        return response

    @retry(on_error=VNXLockRequiredException)
    def _execute_cmd(self, cmd, retry_patterns=None, check_exit_code=False):
        """Execute NAS command via SSH.

        :param retry_patterns: list of tuples,where each tuple contains a reg
            expression and a exception.
        :param check_exit_code: Boolean. Raise
            exception.SSHExecutionError if the command failed to
            execute and this parameter is set to True.
        """
        if not retry_patterns:
            retry_patterns = self.retry_patterns

        try:
            out, err = self.ssh_connector.execute(
                cmd, check_exit_code=check_exit_code)
        except SSHExecutionError as e:
            for pattern in retry_patterns:
                if re.search(pattern[0], e.stdout):
                    raise pattern[1]

            raise e

        return out, err

    @staticmethod
    def _translate_response(response):
        """Translate different status to ok/error status."""
        severity = response['maxSeverity']
        if const.STATUS_OK == severity or const.STATUS_ERROR == severity:
            return

        if severity in (const.STATUS_DEBUG, const.STATUS_INFO):
            response['maxSeverity'] = const.STATUS_OK

            log.warn("Translated status from %(old)s to %(new)s. "
                     "Message: %(info)s.",
                     {'old': severity,
                      'new': response['maxSeverity'],
                      'info': response})

    def _get_mover(self, mover_name, is_vdm):
        vdm_manager = self.manager.get_object_manager('vdm')
        mover_ref_manager = self.manager.get_object_manager('mover_ref')
        if is_vdm:
            mover = vdm_manager.get(mover_name)
        else:
            mover = mover_ref_manager.get(mover_name)

        return mover

    def _response_validation(self, response, error_code):
        """Translate different status to ok/error status."""
        msg_codes = self._get_problem_message_codes(response['problems'])

        for code in msg_codes:
            if code == error_code:
                return True

        return False

    @staticmethod
    def _get_problem_props(problems, key):
        return [problem[key] for problem in problems
                if key in problem]

    @classmethod
    def _get_problem_message_codes(cls, problems):
        return cls._get_problem_props(problems, 'messageCode')

    @classmethod
    def _get_problem_messages(cls, problems):
        return cls._get_problem_props(problems, 'message')

    @classmethod
    def _get_problem_diags(cls, problems):
        return cls._get_problem_props(problems, 'Diagnostics')
