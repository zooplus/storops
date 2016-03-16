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
import six

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


class VNXException(Exception):
    """Base EMC Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will be formatted
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 500
    headers = {}

    def __init__(self, message=None, **kwargs):
        if message is None:
            message = self.message

        self.kwargs = self._insert_default_code(kwargs)
        self.message = self._update_message(message, kwargs)

        super(VNXException, self).__init__(self.message)

    @staticmethod
    def _update_message(message, kwargs):
        if isinstance(message, six.string_types):
            try:
                message = message.format(**kwargs)

            except KeyError:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                log.error(
                    'missing param in format string: "{}"'.format(message))
            except IndexError:
                # format error, use original message
                pass
        elif isinstance(message, Exception):
            message = six.text_type(message)

        return message

    @classmethod
    def _insert_default_code(cls, kwargs):
        if 'code' not in kwargs:
            try:
                kwargs['code'] = cls.code
            except AttributeError:
                pass
        for k, v in six.iteritems(kwargs):
            if isinstance(v, Exception):
                kwargs[k] = six.text_type(v)
        return kwargs


class NaviseccliNotAvailableError(VNXException):
    message = ("naviseccli not found.  please make sure it's installed"
               " and available in path.")


class VNXObjectNotFound(VNXException):
    message = "object is not found.  {err}"


class OptionMissingError(VNXException):
    pass


class VNXBackendError(VNXException):
    message = "backend error.  {err}"


class VNXInvalidMoverID(VNXException):
    message = "invalid mover or vdm.  {id}"


class VNXLockRequiredException(VNXException):
    message = "unable to acquire lock."


class InvalidParameterValue(VNXException):
    message = "{err}"


class VNXTimeoutError(VNXException):
    pass


class VNXSystemError(VNXException):
    pass


class VNXSystemDownError(VNXSystemError):
    pass


class VNXSPError(VNXException):
    pass


class VNXSPDownError(VNXSPError):
    pass


class VNXNoIndexException(VNXException):
    pass


class VNXStorageGroupError(VNXException):
    pass


class VNXNoHluAvailableError(VNXStorageGroupError):
    pass


class VNXMigrationError(VNXException):
    pass


class VNXSnapError(VNXException):
    pass


class VNXCreateSnapError(VNXException):
    pass


class VNXAttachSnapError(VNXSnapError):
    pass


class VNXDetachSnapError(VNXSnapError):
    pass


class VNXRemoveSnapError(VNXSnapError):
    pass


class VNXLunError(VNXException):
    pass


class VNXCreateLunError(VNXLunError):
    pass


class VNXModifyLunError(VNXLunError):
    pass


class VNXLunExtendError(VNXLunError):
    pass


class VNXLunExpandSizeError(VNXLunExtendError):
    pass


class VNXLunNotFoundError(VNXLunError):
    pass


class VNXRemoveLunError(VNXLunError):
    pass


class VNXCompressionError(VNXLunError):
    pass


class VNXDedupError(VNXLunError):
    pass


class VNXConsistencyGroupError(VNXException):
    pass


class VNXCreateConsistencyGroupError(VNXConsistencyGroupError):
    pass


class VNXRaidGroupError(VNXException):
    pass


class VNXCreateRaidGroupError(VNXRaidGroupError):
    pass


class VNXRemoveRaidGroupError(VNXRaidGroupError):
    pass


class VNXPoolError(VNXException):
    pass


class VNXCreatePoolError(VNXPoolError):
    pass


class VNXModifyPoolError(VNXPoolError):
    pass


class VNXRemovePoolError(VNXPoolError):
    pass


class VNXFsError(VNXException):
    pass


class VNXFsExistedError(VNXFsError):
    pass


class VNXFsSnapError(VNXException):
    pass


class VNXFsSnapExistedError(VNXFsSnapError):
    pass


class VNXMoverInterfaceError(VNXException):
    pass


class VNXMoverInterfaceNotFound(VNXException):
    pass


class VNXMoverInterfaceNotAttached(VNXException):
    pass
