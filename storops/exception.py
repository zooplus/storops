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

__rest_exception_clz_list__ = []


def rest_exception(clz):
    if not hasattr(clz, 'error_code'):
        raise AttributeError('error_code property is missing.')
    if clz not in __rest_exception_clz_list__:
        __rest_exception_clz_list__.append(clz)
    return clz


def get_rest_exception(error_code):
    ret = UnityException
    if error_code is not None:
        for clz in __rest_exception_clz_list__:
            if clz.error_code == error_code:
                ret = clz
                break
    return ret


class StoropsException(Exception):
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

        super(StoropsException, self).__init__(self.message)

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


class EnumValueNotFoundError(StoropsException):
    pass


class MockFileNotFoundError(StoropsException):
    pass


class NoIndexException(StoropsException):
    pass


class UnityException(StoropsException):
    error_code = None

    def __init__(self, error):
        self.error = error

    def __str__(self):
        if hasattr(self.error, 'get_messages'):
            ret = '.  '.join(self.error.get_messages())
        else:
            ret = self.error
        return ret


class UnityNameNotUniqueError(UnityException):
    pass


@rest_exception
class UnityResourceNotFoundError(UnityException):
    error_code = 131149829


@rest_exception
class UnityNasServerNameUsedError(UnityException):
    error_code = 108011556


@rest_exception
class UnityIpAddressUsedError(UnityException):
    error_code = 108011747


@rest_exception
class UnityOneDnsPerNasServerError(UnityException):
    error_code = 108012064


@rest_exception
class UnitySmbShareNameExistedError(UnityException):
    error_code = 151036420


@rest_exception
class UnityNfsShareNameExistedError(UnityException):
    error_code = 151036164


@rest_exception
class UnityOneSmbServerPerNasServerError(UnityException):
    error_code = 108011888


@rest_exception
class UnityNetBiosNameExistedError(UnityException):
    error_code = 108011876


@rest_exception
class UnityNfsAlreadyEnabledError(UnityException):
    error_code = 108012128


@rest_exception
class UnityFileSystemNameAlreadyExisted(UnityException):
    error_code = 108008464


@rest_exception
class UnitySnapNameInUseError(UnityException):
    error_code = 1903001605


class VNXException(StoropsException):
    pass


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


class VNXStorageGroupError(VNXException):
    pass


class VNXNoHluAvailableError(VNXStorageGroupError):
    pass


class VNXMigrationError(VNXException):
    pass


class VNXTargetNotReadyError(VNXMigrationError):
    pass


class VNXSnapError(VNXException):
    pass


class VNXCreateSnapError(VNXException):
    pass


class VNXAttachSnapError(VNXSnapError):
    pass


class VNXDetachSnapError(VNXSnapError):
    pass


class VNXSnapNameExistedError(VNXSnapError):
    pass


class VNXRemoveSnapError(VNXSnapError):
    pass


class VNXSnapNotExistsError(VNXSnapError):
    pass


class VNXLunError(VNXException):
    pass


class VNXCreateLunError(VNXLunError):
    pass


class VNXLunNameInUseError(VNXCreateLunError):
    pass


class VNXModifyLunError(VNXLunError):
    pass


class VNXLunExtendError(VNXLunError):
    pass


class VNXLunExpandSizeError(VNXLunExtendError):
    pass


class VNXLunPreparingError(VNXLunError):
    pass


class VNXLunNotFoundError(VNXLunError):
    pass


class VNXRemoveLunError(VNXLunError):
    pass


class VNXCompressionError(VNXLunError):
    pass


class VNXCompressionAlreadyEnabledError(VNXCompressionError):
    pass


class VNXDedupError(VNXLunError):
    pass


class VNXConsistencyGroupError(VNXException):
    pass


class VNXCreateConsistencyGroupError(VNXConsistencyGroupError):
    pass


class VNXConsistencyGroupNameInUseError(VNXCreateConsistencyGroupError):
    pass


class VNXConsistencyGroupNotFoundError(VNXConsistencyGroupError):
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
