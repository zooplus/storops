# coding=utf-8
from __future__ import unicode_literals

import logging
import re
import six

__author__ = 'Cedric Zhuang'

LOG = logging.getLogger(__name__)


class EMCException(Exception):
    """Base EMC Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 500
    headers = {}

    def __init__(self, message=None, detail_data=None, **kwargs):
        if detail_data is None:
            detail_data = {}

        self.kwargs = kwargs
        self.detail_data = detail_data

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass
        for k, v in six.iteritems(self.kwargs):
            if isinstance(v, Exception):
                self.kwargs[k] = six.text_type(v)

        if not message:
            try:
                message = self.message % kwargs

            except TypeError:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation.')
                for name, value in six.iteritems(kwargs):
                    LOG.error("%(name)s: %(value)s", {
                        'name': name, 'value': value})
                else:
                    # at least get the core message out if something happened
                    message = self.message
        elif isinstance(message, Exception):
            message = six.text_type(message)

        if re.match('.*[^\.]\.\.$', message):
            message = message[:-1]
        self.msg = message
        super(EMCException, self).__init__(message)


class VNXException(EMCException):
    pass


class NaviseccliNotAvailableError(VNXException):
    message = ("naviseccli not found.  please make sure it's installed"
               " and available in path.")


class ObjectNotFound(EMCException):
    message = "[EMC] Object is not found. %(err)s."


class OptionMissingError(EMCException):
    pass


class BackendError(VNXException):
    message = "[EMC] Backend error. %(err)s."


class VNXBackendError(VNXException):
    message = "[EMC] VNX Backend error. %(err)s."


class VNXInvalidMoverID(VNXException):
    message = "[EMC] Invalid mover or vdm %(id)s."


class VNXLockRequiredException(VNXException):
    message = "[EMC] Unable to acquire lock(s)."


class InvalidParameterValue(EMCException):
    message = "%(err)s"


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


class VNXAttachSnapError(VNXSnapError):
    pass


class VNXDetachSnapError(VNXSnapError):
    pass


class VNXLunError(VNXException):
    pass


class VNXModifyLunError(VNXLunError):
    pass


class VNXCompressionError(VNXLunError):
    pass


class VNXDedupError(VNXLunError):
    pass


class VNXConsistencyGroupError(VNXException):
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
