# coding=utf-8
from __future__ import unicode_literals

__author__ = 'Cedric Zhuang'


class VNXException(Exception):
    pass


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
