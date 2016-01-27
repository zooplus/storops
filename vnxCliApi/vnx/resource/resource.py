# coding=utf-8
from __future__ import unicode_literals

import json

import six

from vnxCliApi.vnx.parsers import PropDescriptor, get_parser_config
from vnxCliApi import exception as ex

__author__ = 'Cedric Zhuang'


class VNXResource(object):
    def __init__(self):
        super(VNXResource, self).__init__()
        self._property_cache = {}
        self._parsed_resource = None

    @staticmethod
    def _get(data, key):
        if isinstance(key, PropDescriptor):
            key = key.key
        try:
            ret = data.__getitem__(key)
        except KeyError:
            ret = None
        return ret

    @staticmethod
    def _has_get(data):
        return hasattr(data, '__getitem__')

    @classmethod
    def _get_float_value(cls, data, descriptor):
        if isinstance(data, six.string_types):
            ret = float(data)
        elif cls._has_get(data):
            ret = cls._get(data, descriptor)
        elif isinstance(data, float):
            ret = data
        elif cls._is_int_or_str(data):
            ret = float(data)
        else:
            raise ValueError('Cannot convert input to float.  Value: {}'
                             .format(data))
        return ret

    @staticmethod
    def _is_int_or_str(data):
        is_int = isinstance(data, six.integer_types)
        is_str = isinstance(data, six.text_type)
        return is_int or is_str

    @classmethod
    def _get_integer_value(cls, data, descriptor):
        if isinstance(data, six.string_types):
            ret = int(data)
        elif cls._has_get(data):
            ret = cls._get(data, descriptor)
        elif isinstance(data, float):
            ret = int(round(data))
        elif cls._is_int_or_str(data):
            ret = int(data)
        else:
            raise ValueError('Cannot convert input to integer.  Value: {}'
                             .format(data))
        return ret

    @classmethod
    def _get_text_value(cls, data, *descriptors):
        ret = None
        for descriptor in descriptors:
            if isinstance(data, six.string_types):
                ret = data
            elif cls._has_get(data):
                ret = cls._get(data, descriptor)
            else:
                raise ValueError('Cannot convert input to text.  Value: {}'
                                 .format(data))
            if ret is not None:
                break
        return ret

    def _get_name(self):
        if self._name is not None:
            name = self._name
        else:
            name = self.name
        return name

    @classmethod
    def _get_parser(cls):
        # use class name as the default
        return get_parser_config(cls.__name__)

    def update(self, data=None):
        if data is None:
            data = self._get_raw_resource()

        if isinstance(data, dict):
            self._parsed_resource = data
        else:
            self._parsed_resource = self._parse_cli(data)
        return self

    def get_index(self):
        parser = self._get_parser()
        index_desc = parser.get_index_descriptor()
        if index_desc is not None:
            ret = getattr(self, index_desc.key)
        else:
            raise ex.VNXNoIndexException('{} does not have index.'
                                         .format(self.__class__.__name__))
        return ret

    @property
    def existed(self):
        try:
            ret = self.get_index() is not None
        except ex.VNXNoIndexException:
            # no index, check if any of the property is available
            prop = self._get_first_not_none_prop()
            ret = prop is not None
        return ret

    def _get_first_not_none_prop(self):
        ret = None
        prop_desc_list = self._get_parser().get_all_property_descriptor()
        for prop_desc in prop_desc_list:
            ret = getattr(self, prop_desc.key)
            if ret is not None:
                break
        return ret

    def is_valid(self):
        return self.existed()

    def _get_parsed_resource(self):
        return self._get_raw_resource()

    def _parse_cli(self, data):
        return self._get_parser().parse(data)

    @classmethod
    def parse(cls, output):
        obj = cls()
        data = cls._get_parser().parse_single(output)
        return obj.update(data)

    @classmethod
    def parse_all(cls, output):
        ret = []
        for data in cls._get_parser().parse_all(output):
            obj = cls()
            ret.append(obj.update(data))
        return ret

    def get_dict_repr(self):
        props = self._get_properties()
        return {self.__class__.__name__: props}

    def json(self, indent=None):
        return json.dumps(self.get_dict_repr(), indent=indent)

    def __repr__(self):
        return self.json(indent=4)

    def __str__(self):
        return self.json()

    def _get_property_names(self):
        return [name.key for name in self._get_parser().get_all()]

    def _get_properties(self):
        props = {'hash': self.__hash__()}

        prop_names = self._get_property_names()
        prop_names.append('existed')
        for name in prop_names:
            try:
                value = getattr(self, name)
                if isinstance(value, VNXCliResource):
                    value = value.get_dict_repr()
                props[name] = value
            except AttributeError:
                # skip not available attributes
                continue
        return props

    @property
    def _cache_size(self):
        return len(self._property_cache)

    # noinspection PyMethodMayBeStatic
    def _get_raw_resource(self):
        """get raw input of this resource

        Get the raw input of this resource.
        The input could be retrieved from multiple interface like
        CLI or CIM."""
        return ''

    def __getattr__(self, item):
        try:
            ret = super(object, self).__getattr__(item)
        except AttributeError as e:
            if item in self._property_cache:
                ret = self._property_cache[item]
            elif item[0] != '_':
                ret = self._get_property_from_raw(item)
            else:
                raise e
        return ret

    def _get_property_from_raw(self, item):
        ret = None
        parser = self._get_parser()
        if self._parsed_resource is None:
            self.update()
        if parser is not None and self._parsed_resource:
            mapper_key = 'key'
            for property_mapper in parser.get_all():
                key = property_mapper.key
                if key == item:
                    ret = self._parsed_resource[
                        getattr(property_mapper, str(mapper_key))]
                    if property_mapper.cache:
                        self._property_cache[key] = ret
                    break
            else:
                raise AttributeError(
                    "'{}' does not contain attribute '{}'".format(
                        self.__class__.__name__, item))
        return ret

    def _is_client_available(self):
        return '_cli' in dir(self) and getattr(self, '_cli') is not None


class _WithPoll(object):
    def __init__(self, r):
        self._resource = r
        self._orig_poll = self._resource.poll

    def __enter__(self):
        pass

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        # return None, do not handle inner exception
        self._resource.poll = self._orig_poll


class VNXCliResource(VNXResource):
    def __init__(self):
        super(VNXCliResource, self).__init__()
        self.poll = True

    def with_poll(self):
        ret = _WithPoll(self)
        self.poll = True
        return ret

    def with_no_poll(self):
        ret = _WithPoll(self)
        self.poll = False
        return ret


class VNXResourceList(VNXCliResource):
    def __init__(self):
        super(VNXResourceList, self).__init__()
        self._list = []
        self._iter = None

    def update(self, data=None):
        self._list = []
        if data is None:
            data = self._get_raw_resource()

        if data is not None and isinstance(data, dict):
            parsed_list = data
        else:
            parsed_list = self._parse_cli(data)

        for i in parsed_list:
            item = self.get_resource_class()()
            item.update(i)
            self._list.append(item)
        return self

    def _parse_cli(self, data):
        return self._get_parser().parse_all(data)

    @classmethod
    def _get_parser(cls):
        return get_parser_config(cls.get_resource_class().__name__)

    @property
    def list(self):
        if not self._list:
            self.update()
        return self._list

    @classmethod
    def get_resource_class(cls):
        raise NotImplementedError(
            'should return the class ref of the resource in the list.')

    def get_dict_repr(self):
        items = [item.get_dict_repr() for item in self.list]
        return {self.__class__.__name__: items}

    def __len__(self):
        return len(self.list)

    def __iter__(self):
        self._iter = self.list.__iter__()
        return self

    def next(self):
        return six.next(self._iter)

    def __next__(self):
        return self.next()

    def __getitem__(self, item):
        return self.list[item]


# noinspection PyAbstractClass
class VNXCliResourceList(VNXResourceList):
    def __init__(self, cli=None):
        super(VNXCliResourceList, self).__init__()
        self._cli = cli

    def update(self, data=None):
        ret = super(VNXCliResourceList, self).update(data)
        for item in self._list:
            item._cli = self._cli
        return ret
