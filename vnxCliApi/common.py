import logging
from collections import defaultdict

from six import string_types
from threading import Timer, Lock, Thread

log = logging.getLogger(__name__)


class Enum(object):
    @classmethod
    def get_all(cls):
        return [getattr(cls, member) for member in dir(cls)
                if cls._is_enum(member)]

    @classmethod
    def _is_enum(cls, name):
        return (isinstance(name, string_types) and
                hasattr(cls, name) and name.isupper())

    @classmethod
    def get_opt(cls, value):
        option_map = getattr(cls, '_option_map', None)
        if option_map is None:
            raise NotImplementedError('Option map is not defined for {}.'
                                      .format(cls.__name__))

        ret = option_map.get(value, None)
        if ret is None:
            raise ValueError("{} is not a valid option for {}."
                             .format(value, cls.__name__))
        return ret

    @classmethod
    def from_int(cls, value):
        int_index = getattr(cls, '_int_index', None)
        if int_index is None:
            raise NotImplementedError('Integer index is not defined for {}.'
                                      .format(cls.__name__))

        found = False
        try:
            ret = int_index[value]
            found = True
        except IndexError:
            ret = None

        if not found or ret is None:
            raise ValueError('{} is not a valid value for {}.'
                             .format(cls.__name__))
        return ret


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


class Cache(object):
    _cache = defaultdict(lambda: {})

    lock_map_lock = Lock()
    lock_map = {}

    def __init__(self):
        pass

    @staticmethod
    def get_key(func):
        return func.__hash__()

    @classmethod
    def get_cache(cls, func):
        return cls._cache[cls.get_key(func)]

    @classmethod
    def clear_func_cache(cls, func):
        cls._cache[cls.get_key(func)] = {}

    @classmethod
    def get_cache_lock(cls, key):
        if key not in cls.lock_map:
            cls.lock_map[key] = Lock()
        return cls.lock_map[key]

    @classmethod
    def cache(cls, seconds=None):
        def clear_cache(cache, key):
            if key in cache:
                del (cache[key])

        def decorator(func):
            def _key_gen(*args, **kwargs):
                return args, hash(frozenset(kwargs.items()))

            def func_wrapper(*args, **kwargs):
                key = _key_gen(*args, **kwargs)
                cache = cls.get_cache(func)
                if key in cache:
                    ret = cache[key]
                else:
                    ret = func(*args, **kwargs)
                    lock = cls.get_cache_lock(func)
                    lock.acquire()
                    if key in cache:
                        ret = cache[key]
                    else:
                        cache[key] = ret
                        if seconds is not None:
                            Timer(seconds, clear_cache, (cache, key)).start()
                    lock.release()
                return ret

            return func_wrapper

        return decorator


def background(func_ref, *args, **kwargs):
    if not callable(func_ref):
        raise ValueError('background only accept callable inputs.')
    t = Thread(target=func_ref, args=args, kwargs=kwargs)
    t.setDaemon(True)
    t.start()
    return t
