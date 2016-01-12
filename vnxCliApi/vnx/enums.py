# coding=utf-8
from __future__ import unicode_literals

import logging
import re

import six

from vnxCliApi.lib.common import Enum

log = logging.getLogger(__name__)


class VNXSPEnum(Enum):
    SP_A = 'SP A'
    SP_B = 'SP B'
    CONTROL_STATION = 'Celerra'

    _int_index = (None, SP_A, SP_B, CONTROL_STATION)

    to_remove = re.compile('[_. ]')

    @classmethod
    def is_sp(cls, name):
        name = cls.from_str(name)
        return name in (cls.SP_A, cls.SP_B)

    @classmethod
    def _normalize(cls, value):
        ret = re.sub(cls.to_remove, '', value)
        if ret is None:
            pass
        elif ret.endswith('a') and not ret.endswith('rra'):
            ret = 'spa'
        elif ret.endswith('b'):
            ret = 'spb'
        elif ret == 'cs':
            ret = 'celerra'
        return ret

    @classmethod
    def from_str(cls, value):
        value = value.lower()
        value = cls._normalize(value)
        ret = None
        for item in cls.get_all():
            if cls._normalize(item.lower()) in value:
                ret = item
                break
        else:
            log.warn('cannot parse "{}" to a vnx sp.'.format(value))
        return ret

    @classmethod
    def get_sp_index(cls, value):
        value = cls.from_str(value)
        if value is None:
            raise ValueError('"{}" is not a valid sp name.'.format(value))
        return value.lower()[-1]


class VNXProvisionEnum(Enum):
    # value of spec "provisioning:type"
    THIN = 'thin'
    THICK = 'thick'
    COMPRESSED = 'compressed'
    DEDUPED = 'deduplicated'

    _option_map = {
        THIN: ['-type', 'Thin'],
        THICK: ['-type', 'NonThin'],
        COMPRESSED: ['-type', 'Thin'],
        DEDUPED: ['-type', 'Thin', '-deduplication', 'on']}


class VNXCompressionRate(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class VNXTieringPreference(Enum):
    INVALID = 0
    NONE = 1
    LOWEST_AVAILABLE = 2
    HIGHEST_AVAILABLE = 3


class VNXRelocationPolicy(Enum):
    INVALID = 0
    NONE = 1
    TIER_PREFERENCE = 2
    OPTIMAL = 3


class VNXMigrationRate(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    ASAP = 'asap'


class VNXTieringEnum(Enum):
    NONE = 'none'
    HIGH_AUTO = 'starthighthenauto'
    AUTO = 'auto'
    HIGH = 'highestavailable'
    LOW = 'lowestavailable'
    NO_MOVE = 'nomovement'

    _option_map = {
        NONE: [],
        HIGH_AUTO: [
            '-initialTier', 'highestAvailable',
            '-tieringPolicy', 'autoTier'],
        AUTO: [
            '-initialTier', 'optimizePool',
            '-tieringPolicy', 'autoTier'],
        HIGH: [
            '-initialTier', 'highestAvailable',
            '-tieringPolicy', 'highestAvailable'],
        LOW: [
            '-initialTier', 'lowestAvailable',
            '-tieringPolicy', 'lowestAvailable'],
        NO_MOVE: [
            '-initialTier', 'optimizePool',
            '-tieringPolicy', 'noMovement']
    }

    @classmethod
    def get_tier(cls, initial, policy):
        ret = None
        for k, v in cls._option_map.items():
            if len(v) >= 4:
                v_initial, v_policy = v[1], v[3]
                if (cls.match_option(initial, v_initial) and
                        cls.match_option(policy, v_policy)):
                    ret = k
                    break
                elif cls.match_option(policy, 'noMovement'):
                    """no movement could have different initial tier"""
                    ret = cls.NO_MOVE
                    break
        if ret is None:
            raise ValueError('Initial tier: {}, policy: {} is not valid.'
                             .format(initial, policy))
        return ret

    @staticmethod
    def match_option(output, option):
        return output.replace(' ', '').lower() == option.lower()


class VNXError(Enum):
    GENERAL_NOT_FOUND = ('cannot find|'
                         'may not exist|'
                         'does not exist|'
                         'cannot be found')

    SP_NOT_AVAILABLE = ('^Error.*Message.*End of data stream.*|'
                        '.*Message.*connection refused.*|'
                        '^Error.*Message.*Service Unavailable.*|'
                        '^A network error occurred while trying to connect.*|'
                        '^Exception: Error occurred because of time out\s*')
    NOT_A_SP = ('.*CLI commands are not supported '
                'by the target storage system.*')

    SG_NAME_IN_USE = 'Storage Group name already in use'
    SG_LUN_ALREADY_EXISTS = ('LUN already exists in the '
                             'specified storage group|'
                             'Requested LUN has already '
                             'been added to this Storage Group')
    SG_HOST_LUN_NOT_EXISTS = 'No such Host LUN in this Storage Group'
    SG_HOST_LUN_USED = ('Requested Host LUN Number already in use|'
                        'LUN mapping still exists')

    LUN_ALREADY_EXPANDED = 0x712d8e04
    LUN_EXISTED = 0x712d8d04
    LUN_IS_PREPARING = 0x712d8e0e
    LUN_IN_SG = 'contained in a Storage Group|LUN mapping still exists'
    LUN_NOT_MIGRATING = ('The specified source LUN is '
                         'not currently migrating')
    LUN_IS_NOT_SMP = 'it is not a snapshot mount point'

    CG_IS_DELETING = 0x712d8801
    CG_EXISTED = 0x716d8021
    CG_SNAP_NAME_EXISTED = 0x716d8005

    SNAP_NAME_EXISTED = 0x716d8005
    SNAP_NAME_IN_USE = 0x716d8003
    SNAP_ALREADY_MOUNTED = 0x716d8055
    SNAP_NOT_ATTACHED = ('The specified Snapshot mount point '
                         'is not currently attached.')

    @staticmethod
    def _match(output, error_code):
        is_match = False
        if VNXError._is_enum(error_code):
            error_code = getattr(VNXError, error_code)

        if isinstance(error_code, int):
            error_code = hex(error_code)

        if hasattr(output, 'message'):
            output = output.message
        elif hasattr(output, 'why'):
            # for EvError
            output = getattr(output, 'why')
        else:
            try:
                output = output.get('why')
            except AttributeError:
                pass

        if isinstance(error_code, six.string_types):
            error_code = error_code.strip()
            flags = re.IGNORECASE | re.MULTILINE | re.DOTALL
            found = re.findall(error_code, output,
                               flags=flags)
            is_match = len(found) > 0

        return is_match

    @classmethod
    def has_error(cls, output, *error_codes):
        if error_codes is None or len(error_codes) == 0:
            error_codes = VNXError.get_all()
        return any([cls._match(output, error_code)
                    for error_code in error_codes])

    @classmethod
    def sp_not_available(cls, out):
        return len(out) < 500 and has_error(out, cls.SP_NOT_AVAILABLE)


def has_error(output, *error_codes):
    return VNXError.has_error(output, *error_codes)


class VNXPortType(Enum):
    FC = 'FC'
    ISCSI = 'iSCSI'
    FCOE = 'FCoE'
    SAS = 'SAS'

    _int_index = (None, FC, ISCSI, FCOE, SAS)


class VNXSnapType(Enum):
    LUN = 1
    CG = 2


class VNXMirrorViewRecoveryPolicy(Enum):
    MANUAL = 'manual'
    AUTO = 'automatic'

    _option_map = {
        MANUAL: ['-recoverypolicy', 'manual'],
        AUTO: ['-recoverypolicy', 'auto']
    }


class VNXMirrorViewSyncRate(Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class VNXLunType(Enum):
    THIN = 'Thin'
    NON_THIN = 'NonThin'
    SNAP = 'Snap'
    SNAP_MOUNT_POINT = 'Snap'
    COMPRESSED = 'Compressed'
    NON_COMPRESSED = 'NonCompressed'
    DEDUPED = 'Deduped'
    NON_DEDUPED = 'NonDeduped'


class VNXRaidType(Enum):
    RAID0 = 'r0'
    RAID1 = 'r1'
    RAID2 = 'r2'
    RAID3 = 'r3'
    RAID4 = 'r4'
    RAID5 = 'r5'
    RAID6 = 'r6'
    RAID10 = 'r1_0'


class VNXPoolRaidType(Enum):
    RAID5 = 'r_5'
    RAID6 = 'r_6'
    RAID10 = 'r_10'
