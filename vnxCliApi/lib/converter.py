# coding=utf-8
from __future__ import unicode_literals

import logging
import re
from datetime import datetime
from functools import partial
from operator import is_not

from past.builtins import filter
import six

from vnxCliApi.vnx.enums import VNXSPEnum, VNXMirrorViewSyncRate, \
    VNXMirrorViewRecoveryPolicy, VNXRaidType

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)

NAs = ['N/A', 'Unbound']


def to_bool(str_input):
    ret = False
    if str_input.strip().lower() in ('yes', 'true', 'enabled', 'on'):
        ret = True
    return ret


def to_int_arr(str_input):
    def to_int_silent_error(value):
        ret = None
        try:
            if len(value) > 0:
                ret = int(value)
        except ValueError:
            if value not in NAs:
                log.warn('cannot convert "{}" to int.'.format(value))
        return ret

    ints = map(to_int_silent_error, re.split(',| ', str_input))
    return list(filter(partial(is_not, None), ints))


def to_int_str_map(str_input):
    ret = {}
    for pair in re.findall('(\w+):\s*(\w+)', str_input):
        ret[to_int(pair[0])] = pair[1].strip()
    return ret


def to_int_int_map(str_input):
    ret = {}
    for pair in re.findall('(\w+):\s*(\w+)', str_input):
        ret[to_int(pair[0])] = to_int(pair[1])
    return ret


def arr_to_str(int_arr, sep=None):
    if sep is None:
        sep = ','
    return sep.join((six.text_type(i) for i in int_arr))


def to_str_arr(int_arr):
    return [six.text_type(i) for i in int_arr]


def to_float(value):
    ret = None
    if value is not None:
        try:
            ret = float(value)
        except ValueError:
            pass
    return ret


def to_int(value):
    ret = None
    if value is not None:
        try:
            ret = int(value)
        except ValueError:
            pass
    return ret


def to_alu_hlu_map(input_str):
    """Converter for alu hlu map

    Convert following input into a alu -> hlu map:
    Sample input:

    ```
      HLU Number     ALU Number
      ----------     ----------
        0               12
        1               23
    ```

    ALU stands for array LUN number
    hlu stands for host LUN number
    :param input_str: raw input from naviseccli
    :return: alu -> hlu map
    """
    ret = {}
    if input_str is not None:
        pattern = re.compile(r'(\d+)\s*(\d+)')
        for line in input_str.split('\n'):
            line = line.strip()
            if len(line) == 0:
                continue
            matched = re.search(pattern, line)
            if matched is None or len(matched.groups()) < 2:
                continue
            else:
                hlu = matched.group(1)
                alu = matched.group(2)
                ret[int(alu)] = int(hlu)
    return ret


def to_disk_indices(value):
    """Convert following input to disk indices

    Sample input:

    ```
    Disks:
    Bus 0 Enclosure 0 Disk 9
    Bus 1 Enclosure 0 Disk 12
    Bus 1 Enclosure 0 Disk 9
    Bus 0 Enclosure 0 Disk 4
    Bus 0 Enclosure 0 Disk 7
    ```

    :param value: disk list
    :return: disk indices in list
    """
    ret = []
    p = re.compile(r'Bus\s+(\w+)\s+Enclosure\s+(\w+)\s+Disk\s+(\w+)')
    if value is not None:
        for line in value.split('\n'):
            line = line.strip()
            if len(line) == 0:
                continue
            matched = re.search(p, line)
            if matched is None or len(matched.groups()) < 3:
                continue
            else:
                ret.append('{}_{}_{}'.format(*matched.groups()))
    return ret


def vnx_time_to_date(value):
    return datetime.utcfromtimestamp(value - 2177452800)


def _to_enum(enum_class):
    def _enum_converter(value):
        return enum_class.from_str(value)

    return _enum_converter


to_sp_enum = _to_enum(VNXSPEnum)
to_mirror_view_recovery_policy = _to_enum(VNXMirrorViewRecoveryPolicy)
to_mirror_view_sync_rate = _to_enum(VNXMirrorViewSyncRate)
to_raid_type = _to_enum(VNXRaidType)


def boolean_to_str(value, true_str='true', false_str='false'):
    if value:
        ret = true_str
    else:
        ret = false_str
    return ret
