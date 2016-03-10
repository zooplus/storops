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


from multiprocessing.pool import ThreadPool
from time import sleep
from unittest import TestCase

from hamcrest import assert_that, equal_to, close_to, only_contains

from storops.lib.common import Dict, Enum, WeightedAverage, \
    synchronized, cache, text_var, int_var, enum_var, yes_no_var
from storops.vnx.enums import VNXRaidType


class DictTest(TestCase):
    def test_get_attr(self):
        result = Dict()
        result['a'] = 'A'
        self.assertEqual('A', result.a)
        self.assertEqual('A', result['a'])

    def test_get_attr_not_exists(self):
        result = Dict()
        self.assertRaises(AttributeError, getattr, result, 'a')


class SampleEnum(Enum):
    def __init__(self):
        pass

    TYPE_A = 'type a'
    TYPE_B = 'type b'

    _option_map = {
        None: [],
        TYPE_A: '-a',
        TYPE_B: '-b'
    }

    _int_index = (None, TYPE_A, TYPE_B)


class EnumTest(TestCase):
    def test_get_all(self):
        self.assertEqual(2, len(SampleEnum.get_all()))

    def test_get_opt(self):
        self.assertEqual('-a', SampleEnum.get_opt(SampleEnum.TYPE_A))

    def test_from_int(self):
        self.assertEqual(SampleEnum.TYPE_B, SampleEnum.from_int(2))


class CacheA(object):
    def __init__(self):
        self.base = 0
        pass

    @cache(0.02)
    def do(self, a, b):
        return a + b * 2 + self.base

    @cache()
    def a(self):
        return self.base


class CacheB(object):
    def __init__(self):
        self.base = 0
        pass

    @cache()
    def do(self, a, b):
        return a + b

    @cache()
    def b(self):
        return CacheA().a()


class CacheTest(TestCase):
    def setUp(self):
        self.a = CacheA()
        self.b = CacheB()

    def test_cache(self):
        self.assertEqual(10, self.a.do(2, 4))
        self.a.base = 1
        self.assertEqual(10, self.a.do(2, 4))

        self.assertEqual(6, self.b.do(2, 4))
        self.b.base = 1
        self.assertEqual(6, self.b.do(2, 4))

    def test_cache_expired(self):
        self.assertEqual(10, self.a.do(2, 4))
        self.a.base = 1
        self.assertEqual(10, self.a.do(2, 4))
        self.assertEqual(12, self.a.do(3, 4))
        sleep(0.04)
        self.assertEqual(11, self.a.do(2, 4))

    def test_cache_lock(self):
        assert_that(CacheB().b(), equal_to(0))


class WeightedAverageTest(TestCase):
    def test_data_full(self):
        avg = WeightedAverage(3)
        avg.add(30, 24, 18, 12, 6)
        assert_that(avg.value(), equal_to(10))
        avg.add(30)
        assert_that(avg.value(), equal_to(19))

    def test_data_full_1(self):
        avg = WeightedAverage(6)
        avg.add(30, 24, 18, 12, 6, 6, 6)
        assert_that(avg.value(), close_to(8.85, 0.01))
        avg.add(30)
        assert_that(avg.value(), equal_to(14))

    def test_data_not_full(self):
        avg = WeightedAverage(3)
        avg.add(12, 6)
        assert_that(avg.value(), equal_to(8.4))

    def test_data_empty(self):
        avg = WeightedAverage(3)
        assert_that(avg.value(), equal_to(0))

    def test_size(self):
        avg = WeightedAverage(3)
        assert_that(avg.size, equal_to(3))
        avg.weight = [3]
        avg.add(4, 5, 7)
        assert_that(avg.size, equal_to(1))
        assert_that(avg.value(), equal_to(7))


class LockDemo(object):
    name = 1

    def __init__(self):
        self.call_count = 0

    @synchronized(name)
    def foo1(self):
        self.call_count += 1
        sleep(0.05)

    def foo2(self, value):
        @synchronized(value)
        def in_foo2():
            self.call_count += 1
            sleep(0.05)

        in_foo2()

    @synchronized()
    def bar(self, _):
        self.call_count += 1
        sleep(0.05)


class SynchronizedTest(TestCase):
    def test_synchronize(self):
        demo = LockDemo()
        pool = ThreadPool(2)
        pool.imap(demo.bar, range(2))
        sleep(0.04)
        assert_that(demo.call_count, equal_to(1))
        sleep(0.05)
        assert_that(demo.call_count, equal_to(2))

    def test_synchronize_with_different_param(self):
        demo = LockDemo()
        pool = ThreadPool(2)
        pool.imap(demo.foo2, range(2))
        sleep(0.02)
        assert_that(demo.call_count, equal_to(2))

    def test_synchronize_with_same_param(self):
        demo = LockDemo()
        pool = ThreadPool(3)
        pool.imap(demo.foo2, (1, 1))
        pool.apply_async(demo.foo1)
        sleep(0.04)
        assert_that(demo.call_count, equal_to(1))
        sleep(0.05)
        assert_that(demo.call_count, equal_to(2))
        sleep(0.05)
        assert_that(demo.call_count, equal_to(3))


class VarTest(TestCase):
    def test_text_var(self):
        assert_that(text_var('-a', 'a'), only_contains('-a', 'a'))
        assert_that(text_var(None, 'a'), only_contains('a'))
        assert_that(text_var('-a', None), equal_to([]))

    def test_int_var(self):
        assert_that(int_var('-a', '1'), only_contains('-a', 1))
        assert_that(int_var(None, '1'), only_contains(1))
        assert_that(int_var('-a', None), equal_to([]))

    def test_enum_var(self):
        assert_that(enum_var('-a', 'r5', VNXRaidType),
                    only_contains('-a', 'r5'))
        assert_that(enum_var(None, 'r5', VNXRaidType), only_contains('r5'))
        assert_that(enum_var('-a', None, VNXRaidType), equal_to([]))

    def test_yes_no_var(self):
        assert_that(yes_no_var('-a', True), only_contains('-a', 'yes'))
        assert_that(yes_no_var('-a', False), only_contains('-a', 'no'))
        assert_that(yes_no_var('-a', None), equal_to([]))
