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

import json
import logging
import types
from enum import Enum as _Enum
from collections import defaultdict
from functools import partial

import functools
import six
import time

import sys
from retryz import retry
from threading import Lock, Thread

import storops.exception

log = logging.getLogger(__name__)


class JsonPrinter(object):
    def _get_properties(self, dec=0):
        raise NotImplementedError('need a property-value dictionary')

    def get_dict_repr(self, dec=0):
        props = self._get_properties(dec)
        props = dict((k, v) for k, v in props.items() if v is not None)
        return {self.__class__.__name__: props}

    def json(self, indent=None):
        return json.dumps(self.get_dict_repr(), indent=indent, sort_keys=True)

    def __repr__(self):
        return self.json(indent=4)

    def __str__(self):
        return self.json()


class EnumList(JsonPrinter):
    def _get_properties(self, dec=0):
        super(EnumList, self)._get_properties(dec)

    def __init__(self):
        super(EnumList, self).__init__()
        self._list = []
        self._iter = None

    @classmethod
    def get_enum_class(cls):
        raise NotImplementedError('enum class of this list is not defined.')

    @classmethod
    def parse(cls, values):
        ret = None
        if values is not None:
            ret = cls()
            ret._list = [ret.get_enum_class().parse(v) for v in values]
        return ret

    def get_dict_repr(self, dec=0):
        items = [item.get_dict_repr(dec - 1) for item in self.list]
        return {self.__class__.__name__: items}

    @property
    def list(self):
        return self._list

    def __len__(self):
        return len(self.list)

    def __iter__(self):
        self._iter = self.list.__iter__()
        return self

    def next(self):
        return next(self._iter)

    def __next__(self):
        return self.next()

    def __getitem__(self, item):
        return self.list[item]


class Enum(_Enum):
    @classmethod
    def verify(cls, value, allow_none=True):
        if value is None and not allow_none:
            raise ValueError(
                'None is not allowed here for {}.'.format(cls.__name__))
        elif value is not None and not isinstance(value, cls):
            raise ValueError('{} is not an instance of {}.'
                             .format(value, cls.__name__))

    @classmethod
    def get_all(cls):
        return list(cls)

    @classmethod
    def get_opt(cls, value):
        option_map = cls.get_option_map()
        if option_map is None:
            raise NotImplementedError('Option map is not defined for {}.'
                                      .format(cls.__name__))

        ret = option_map.get(value, None)
        if ret is None:
            raise ValueError("{} is not a valid option for {}."
                             .format(value, cls.__name__))
        return ret

    @classmethod
    def parse(cls, value):
        if isinstance(value, six.string_types):
            ret = cls.from_str(value)
        elif isinstance(value, six.integer_types):
            ret = cls.from_int(value)
        elif isinstance(value, cls):
            ret = value
        elif value is None:
            ret = None
        else:
            raise ValueError(
                'not supported value type: {}.'.format(type(value)))
        return ret

    def is_equal(self, value):
        if isinstance(value, six.string_types):
            ret = self.value.lower() == value.lower()
        else:
            ret = self.value == value
        return ret

    @classmethod
    def from_int(cls, value):
        ret = None
        int_index = cls.get_int_index()
        if int_index is not None:
            try:
                ret = int_index[value]
            except IndexError:
                pass
        else:
            try:
                ret = next(i for i in cls.get_all() if i.is_equal(value))
            except StopIteration:
                pass
        if ret is None:
            cls._raise_invalid_value(value)
        return ret

    @classmethod
    def from_str(cls, value):
        ret = None
        if value is not None:
            for item in cls.get_all():
                if item.is_equal(value):
                    ret = item
                    break
            else:
                cls._raise_invalid_value(value)
        return ret

    @classmethod
    def _raise_invalid_value(cls, value):
        msg = '{} is not a valid value for {}.'.format(value, cls.__name__)
        log.warn(msg)
        raise storops.exception.EnumValueNotFoundError(msg)

    @classmethod
    def get_option_map(cls):
        raise None

    @classmethod
    def get_int_index(cls):
        return None

    @classmethod
    def values(cls):
        return [m.value for m in cls.__members__.values()]

    @classmethod
    def enum_name(cls):
        return cls.__name__


class Dict(dict):
    def __getattr__(self, item):
        try:
            # noinspection PyUnresolvedReferences
            ret = super(Dict, self).__getattr__(item)
        except AttributeError:
            if item in self:
                value = self.get(item)
            else:
                raise AttributeError(
                    "'{}' does not contain attribute '{}'".format(
                        __name__, item))
            ret = value
        return ret


def get_config_prop(conf, prop, default=None):
    value = default
    if conf is not None:
        if hasattr(conf, prop):
            value = getattr(conf, prop)
        elif hasattr(conf, '__getitem__'):
            try:
                value = conf[prop]
            except (TypeError, KeyError):
                pass
        else:
            raise ValueError('cannot get property from the config.')
    return value


def _cache_holder():
    return defaultdict(lambda: {})


def _cache_lock_holder():
    return defaultdict(lambda: Lock())


class Cache(object):
    _cache = _cache_holder()
    _lock_map = _cache_lock_holder()

    def __init__(self):
        pass

    @staticmethod
    def get_key(func):
        return func.__hash__()

    @classmethod
    def get_cache(cls, key):
        return cls._cache[key]

    @classmethod
    def clear_cache(cls, func=None):
        if func is not None:
            cls._cache[cls.get_key(func)] = {}
        else:
            cls._cache = _cache_holder()
            cls._lock_map = _cache_lock_holder()

    @classmethod
    def get_cache_lock(cls, key):
        return cls._lock_map[key]

    @staticmethod
    def _clear_cache(val_cache=None, key=None):
        if key in val_cache:
            del (val_cache[key])

    @staticmethod
    def _hash(li):
        return hash(frozenset(li))

    @classmethod
    def result_cache_key_gen(cls, *args, **kwargs):
        return cls._hash(args), cls._hash(kwargs.items())

    @classmethod
    def _get_value_from_cache(cls, func, val_cache, lock, *args, **kwargs):
        key = cls.result_cache_key_gen(*args, **kwargs)
        if key in val_cache:
            ret = val_cache[key]
        else:
            with lock:
                if key in val_cache:
                    ret = val_cache[key]
                else:
                    ret = func(*args, **kwargs)
                    val_cache[key] = ret
        return ret

    @classmethod
    def cache(cls, func):
        """ Global cache decorator

        :param func: the function to be decorated
        :return: the decorator
        """

        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            func_key = cls.get_key(func)
            val_cache = cls.get_cache(func_key)
            lock = cls.get_cache_lock(func_key)

            return cls._get_value_from_cache(
                func, val_cache, lock, *args, **kwargs)

        return func_wrapper

    @staticmethod
    def get_self_root_cache(the_self):
        prop_name = '_self_cache_'
        if not hasattr(the_self, prop_name):
            setattr(the_self, prop_name, _cache_holder())
        return getattr(the_self, prop_name)

    @classmethod
    def get_self_cache(cls, the_self, key):
        self_root_cache = cls.get_self_root_cache(the_self)
        return self_root_cache[key]

    @staticmethod
    def get_self_cache_lock_map(the_self):
        prop_name = '_self_cache_lock_'
        if not hasattr(the_self, prop_name):
            setattr(the_self, prop_name, _cache_lock_holder())
        return getattr(the_self, prop_name)

    @classmethod
    def get_self_cache_lock(cls, the_self, key):
        lock_map = cls.get_self_cache_lock_map(the_self)
        return lock_map[key]

    @classmethod
    def clear_self_cache(cls, the_self):
        lock_map = cls.get_self_cache_lock_map(the_self)
        lock_map.clear()
        self_root_cache = cls.get_self_root_cache(the_self)
        self_root_cache.clear()

    @classmethod
    def instance_cache(cls, func):
        """ Save the cache to `self`

        This decorator take it for granted that the decorated function
        is a method.  The first argument of the function is `self`.

        :param func: function to decorate
        :return: the decorator
        """

        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            if not args:
                raise ValueError('`self` is not available.')
            else:
                the_self = args[0]
            func_key = cls.get_key(func)
            val_cache = cls.get_self_cache(the_self, func_key)
            lock = cls.get_self_cache_lock(the_self, func_key)

            return cls._get_value_from_cache(
                func, val_cache, lock, *args, **kwargs)

        return func_wrapper

    @classmethod
    def clear_instance_cache(cls, func):
        """ clear the instance cache

        Decorate a method of a class, the first parameter is
        supposed to be `self`.
        It clear all items cached by the `instance_cache` decorator.
        :param func: function to decorate
        """

        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            if not args:
                raise ValueError('`self` is not available.')
            else:
                the_self = args[0]

            cls.clear_self_cache(the_self)
            return func(*args, **kwargs)

        return func_wrapper


cache = Cache.cache
instance_cache = Cache.instance_cache
clear_instance_cache = Cache.clear_instance_cache


def check_int(value, allow_none=False):
    def is_digit_str():
        return isinstance(value, six.string_types) and str(value).isdigit()

    def is_int():
        return isinstance(value, int)

    if value is None and allow_none:
        ret = None
    else:
        if is_int():
            pass
        elif is_digit_str():
            value = int(value)
        else:
            raise ValueError('"{}" must be an integer.'.format(value))
        ret = int(value)
    return ret


def check_enum(value, enum_class):
    if hasattr(enum_class, 'get_all'):
        get_all_func = getattr(enum_class, 'get_all')
        candidates = get_all_func()
        parsed_enum = enum_class.parse(value)
        if parsed_enum not in candidates:
            raise ValueError('"{}" is not a valid value.  '
                             'Valid values are: {}'.format(value, candidates))
        else:
            value = parsed_enum.value
    else:
        raise ValueError('{} is not a enum.'.format(enum_class))
    return value


def check_text(value):
    if not isinstance(value, six.string_types):
        raise ValueError('"{}" must be text.'.format(value))
    return value


def daemon(func_ref, *args, **kwargs):
    if not callable(func_ref):
        raise ValueError('background only accept callable inputs.')
    t = Thread(target=func_ref, args=args, kwargs=kwargs)
    t.setDaemon(True)
    t.start()
    return t


class WeightedAverage(object):
    def __init__(self, size=5):
        self._data = []
        # linear weight
        self.weight = list(range(size, 0, -1))

    def add(self, *value):
        # the first input is the latest one.
        self._data = list(value[::-1]) + self._data
        self._data = self._data[:self.size]

    @property
    def size(self):
        return len(self.weight)

    def value(self):
        total = 0.0
        weight = 0.0
        ret = 0.0
        for v, w in zip(self._data, self.weight):
            total += v * w
            weight += w
        if weight != 0.0:
            ret = total / weight

        return ret


def log_enter_exit(func):
    @functools.wraps(func)
    def inner(self, *args, **kwargs):
        cls_name = self.__class__.__name__
        func_name = func.__name__
        log.debug("entering %(cls)s.%(method)s.",
                  {'cls': cls_name,
                   'method': func_name})
        start = time.time()
        ret = func(self, *args, **kwargs)
        end = time.time()
        log.debug("exiting %(cls)s.%(method)s.  "
                  "spent %(duration)s sec. "
                  "return %(return)s.",
                  {'cls': cls_name,
                   'duration': end - start,
                   'method': func_name,
                   'return': ret})
        return ret

    return inner


class SynchronizedDecorator(object):
    lock_map_lock = Lock()
    lock_map = {}

    @classmethod
    def synchronized(cls, obj=None):
        """ synchronize on obj if obj is supplied.

        :param obj: the obj to lock on.  if none, lock to the function
        :return: return of the func.
        """

        def get_key(f, o):
            if o is None:
                key = hash(f)
            else:
                key = hash(o)
            return key

        def get_lock(f, o):
            key = get_key(f, o)
            if key not in cls.lock_map:
                with cls.lock_map_lock:
                    if key not in cls.lock_map:
                        cls.lock_map[key] = Lock()
            return cls.lock_map[key]

        def wrap(f):
            @functools.wraps(f)
            def new_func(*args, **kw):
                with get_lock(f, obj):
                    return f(*args, **kw)

            return new_func

        return wrap


synchronized = SynchronizedDecorator.synchronized


def decorate_all_methods(decorator):
    def _decorate_all_methods(cls):
        for attr_name, attr_val in cls.__dict__.items():
            if (isinstance(attr_val, types.FunctionType) and
                    not attr_name.startswith("_")):
                setattr(cls, attr_name, decorator(attr_val))
        return cls

    return _decorate_all_methods


def const_seconds(value):
    return value


def to_wait(_):
    return const_seconds(30)


retry_per_30_s = partial(retry, wait=to_wait, limit=2)


def _var(func, name, value, *param):
    if value is not None:
        if name is not None:
            ret = [name, func(value, *param)]
        else:
            ret = [func(value, *param)]
    else:
        ret = []
    return ret


text_var = functools.partial(_var, check_text)
int_var = functools.partial(_var, check_int)
enum_var = functools.partial(_var, check_enum)
yes_no_var = functools.partial(_var, lambda b: 'yes' if b else 'no')


class Credential(object):
    def __init__(self, user=None, password=None):
        self.user = user
        self.password = password


def get_clz_from_module(module_name, clz_name):
    ret = None
    if module_name not in sys.modules:
        __import__(module_name)
    module = sys.modules[module_name]
    if hasattr(module, clz_name):
        ret = getattr(module, clz_name)
    return ret


def is_valid(value):
    return value is not None and value != 'N/A' and len(value) > 0
