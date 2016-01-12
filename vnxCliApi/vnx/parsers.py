# coding=utf-8
from __future__ import unicode_literals

import logging
import os
import re
import sys

import six
import yaml

from vnxCliApi.lib import converter as cvt
from vnxCliApi.lib.common import Dict, Cache, cache
from vnxCliApi.vnx.enums import Enum

log = logging.getLogger(__name__)


class PropMapper(object):
    def __init__(self,
                 label,
                 key=None,
                 option=None,
                 cache=False,
                 converter=None):
        self.option = option
        self._label = label
        self._key = key
        self._cache = cache
        self.converter = converter

    @property
    def key(self):
        if self._key is None:
            self._key = self.camel_case_to_under_score(self.label).lower()
        return self._key

    to_remove = re.compile('[\(\)]')
    p0 = re.compile(r"[A-Za-z0-9']+")
    p1 = re.compile(r"([^_])([A-Z]s[a-z]+|[A-Z][a-z]{2})")
    p2 = re.compile(r'([a-z0-9])([A-Z])')

    @classmethod
    def camel_case_to_under_score(cls, value, delimiter='_'):
        value = re.sub(cls.to_remove, '', value)
        value = '_'.join(re.findall(cls.p0, value))
        s1 = re.sub(cls.p1, r'\1_\2', value)
        ret = re.sub(cls.p2, r'\1_\2', s1).lower()
        if delimiter != '_':
            ret = ret.replace('_', delimiter)
        return ret

    @property
    def label(self):
        return self._label.strip()

    @property
    def cache(self):
        return self._cache


class PropDescriptor(PropMapper):
    def __init__(self,
                 option,
                 label,
                 key=None,
                 converter=None,
                 is_index=False,
                 end_pattern=None,
                 is_regex=False,
                 sequence=-1):
        super(PropDescriptor, self).__init__(label,
                                             key=key,
                                             option=option,
                                             converter=converter)
        self._is_index = is_index
        self._pattern = None
        self._end_pattern = None
        self._is_regex = is_regex

        self.end_pattern = end_pattern
        self._validate_config()
        self.sequence = sequence

    def _validate_config(self):
        if self.is_regex and self.end_pattern is not None:
            raise ValueError('"is_regex" and "end_pattern" '
                             'are mutual exclusive.')

    @property
    def is_regex(self):
        return self._is_regex

    @property
    def is_index(self):
        return self._is_index

    @property
    def end_pattern(self):
        return self._end_pattern

    @end_pattern.setter
    def end_pattern(self, value):
        if isinstance(value, six.string_types) or value is None:
            self._end_pattern = value
        else:
            raise ValueError('value must be a string type.')

    @property
    def pattern(self):
        if self._pattern is None:
            flags = re.MULTILINE | re.IGNORECASE
            if self.end_pattern is None:
                if self.is_regex:
                    self._pattern = re.compile(self.label, flags)
                else:
                    self._pattern = re.compile(
                        '^[ \t]*{}[ \t]*(?P<value>.*)[ \t]*$'.format(
                            re.escape(self.label)), flags)
            else:
                # has 'end_pattern' means we need to match
                # multi-lines including return.
                flags |= re.DOTALL
                self._pattern = re.compile(
                    '^\s*{}\s*(?P<value>.*){}'.format(
                        re.escape(self.label),
                        re.escape(self.end_pattern)),
                    flags)
        return self._pattern


class VNXCliParser(Enum):
    data_src = 'cli'

    @classmethod
    @cache()
    def get_all_property_descriptor(cls):
        return list(p for p in cls.get_all()
                    if isinstance(p, PropDescriptor))

    @classmethod
    @cache()
    def all_options(cls):
        return list(d.option for d in cls.get_all() if d.option is not None)

    @classmethod
    @Cache.cache()
    def get_index_descriptor(cls):
        indices = cls.get_index_descriptor_list()
        # make sure only one index for each parser
        if len(indices) == 1:
            ret = indices[0]
        elif len(indices) > 1:
            # find the first index
            indices.sort(key=lambda i: i.sequence)
            ret = indices[0]
            log.info('multiple index configured.  '
                     'use the first one as the splitter of output.  '
                     'first index is: "{}"'.format(ret.label))
        else:
            ret = None

        return ret

    @classmethod
    def get_index_descriptor_list(cls):
        return [p for p in cls.get_all_property_descriptor()
                if p.is_index is True]

    @classmethod
    def get_property_options(cls):
        properties = cls.get_all_property_descriptor()
        return [p.option for p in properties if p.option is not None]

    @classmethod
    def _split_by_index(cls, output):
        flags = re.MULTILINE | re.IGNORECASE
        instances = []

        index_descriptor = cls.get_index_descriptor()
        if index_descriptor is not None:
            index_label = index_descriptor.label
            if not index_descriptor.is_regex:
                index_pattern = re.compile(
                    "(^\s*{})".format(re.escape(index_label)),
                    flags=flags)
            else:
                index_pattern = re.compile(
                    index_descriptor.label,
                    flags=flags)

            last_start = 0
            has_match = False
            if isinstance(output, bytes):
                output = output.decode("utf-8")
            for match in re.finditer(index_pattern, output):
                has_match = True
                start = match.start()
                if start == 0:
                    continue
                else:
                    instances.append(output[last_start:start])
                    last_start = start
            if has_match:
                instances.append(output[last_start:])
        else:
            instances = [output]
        return instances

    @classmethod
    def parse_single(cls, output, properties=None):
        output = output.strip()
        ret = Dict()

        if properties is None:
            properties = cls.get_all_property_descriptor()

        for p in properties:
            matched = re.search(p.pattern, output)

            matched_value = None
            if matched is not None:
                if len(matched.groups()) == 1:
                    value = matched.group(1)
                    value = value.strip()
                else:
                    value = matched.groups()
                converter = p.converter
                if converter is not None:
                    if _is_parser(converter):
                        value = converter.parse_all(value)
                    elif _is_vnx_resource(converter):
                        value = cls._convert_resource(converter, value)
                    elif callable(converter):
                        value = converter(value)
                matched_value = value
            elif p.is_index:
                # index must have a match, skip this invalid input
                ret = Dict()
                break
            ret[p.key] = matched_value
        return ret

    @staticmethod
    def _convert_resource(converter, value):
        # try to find the resource with same name first
        return converter().update(value)

    @classmethod
    def parse_all(cls, output, properties=None):
        output = output.strip()
        split_outputs = cls._split_by_index(output)
        instances = cls._parse_split_output(split_outputs, properties)
        instances = cls._merge_instance_with_same_index(instances)
        return instances

    @classmethod
    def _merge_instance_with_same_index(cls, instances):
        def key_gen(instance):
            str_keys = []
            for index in indices:
                str_keys.append(
                    '{}: {}'.format(index.key, instance[index.key]))
            return ', '.join(str_keys)

        def update_map(instance):
            key = key_gen(instance)
            if key not in idx_inst_map:
                idx_inst_map[key] = instance
            else:
                existed = idx_inst_map[key]
                for k, v in six.iteritems(instance):
                    if k not in existed or v is not None:
                        existed[k] = v

        idx_inst_map = {}
        indices = cls.get_index_descriptor_list()
        list(map(update_map, instances))
        return list(idx_inst_map.values())

    @classmethod
    def _parse_split_output(cls, split_outputs, properties):
        ret = []
        for instance in split_outputs:
            parsed = cls.parse_single(instance, properties)
            if len(parsed) > 0:
                ret.append(parsed)
        return ret

    @classmethod
    def parse(cls, output, properties=None):
        ret = cls.parse_all(output, properties)

        if len(ret) == 0:
            ret = Dict()
        else:
            ret = ret[0]
        return ret


def _get_resource_module():
    res_module = 'vnxCliApi.vnx.resources'
    if res_module not in sys.modules:
        __import__(res_module)
    return sys.modules[res_module]


def _is_parser(c):
    return isinstance(c, type) and issubclass(c, VNXCliParser)


def _is_vnx_resource(name):
    if isinstance(name, type):
        name = name.__name__
    module = _get_resource_module()
    try:
        ret = hasattr(module, name)
    except TypeError:
        ret = False
    return ret


def _get_vnx_resource_clz(name):
    module = _get_resource_module()
    return getattr(module, name)


class VNXCimParser(Enum):
    data_src = 'cim'


@cache()
def get_parser_config(name):
    config_filename = 'parser_configs.yaml'

    def read_properties():
        pwd = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(pwd, config_filename)
        with open(filename, 'r') as stream:
            ret = yaml.load(stream)
        return ret

    def get_converter(converter_str):
        """find converter function reference by name

        find converter by name, converter name follows this convention:

            Class.method

        or:

            method

        The first type of converter class/function must be available in
        current module.
        The second type of converter must be available in `__builtin__`
        (or `builtins` in python3) module.

        :param converter_str: string representation of the converter func
        :return: function reference
        """
        ret = None
        if converter_str is not None:
            converter_desc_list = converter_str.split('.')
            if len(converter_desc_list) == 1:
                converter = converter_desc_list[0]
                # default to module `converter`
                try:
                    ret = getattr(cvt, converter)
                except AttributeError:
                    if _is_vnx_resource(converter):
                        # try resource
                        ret = _get_vnx_resource_clz(converter)
                    else:
                        # try parser config
                        ret = get_parser_config(converter)
            elif len(converter_desc_list) == 2:
                classname, func_name = converter_desc_list
                cls = getattr(sys.modules[__name__], classname)
                ret = getattr(cls, func_name)
            else:
                raise ValueError(
                    'Specified converter not supported: {}'.format(
                        converter_str))
        return ret

    def init_descriptor(prop, seq=-1):
        converter = get_converter(prop.get('converter', None))
        return PropDescriptor(option=prop.get('option', None),
                              label=prop.get('label', None),
                              key=prop.get('key', None),
                              is_index=prop.get('is_index', None),
                              converter=converter,
                              end_pattern=prop.get('end_pattern', None),
                              is_regex=prop.get('is_regex', None),
                              sequence=seq)

    all_props = read_properties()
    if name not in all_props:
        raise ValueError('Cannot find {} in {}.'.format(name, config_filename))

    config = all_props[name]

    properties = []
    for i in range(len(config['properties'])):
        properties.append(init_descriptor(config['properties'][i], i))
    clz_member_map = {}
    for p in properties:
        clz_member_map[p.key.upper()] = p
    clz = type(str(name), (VNXCliParser,), clz_member_map)
    setattr(clz, 'data_src', config['data_src'])
    return clz
