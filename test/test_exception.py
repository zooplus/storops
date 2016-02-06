# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to

from vnxCliApi.exception import VNXException

__author__ = 'Cedric Zhuang'


class DemoException(VNXException):
    message = 'hello, {name}.'


class StrangeException(Exception):
    def __init__(self):
        super(StrangeException, self).__init__('strange exception')


class ExceptionTest(TestCase):
    def test_message(self):
        ex = DemoException(name='Peter')
        assert_that(ex.message, equal_to('hello, Peter.'))

    def test_not_enough_param(self):
        ex = DemoException()
        assert_that(ex.message, equal_to('hello, {name}.'))

    def test_code(self):
        ex = DemoException('code is {code}')
        assert_that(str(ex), equal_to('code is 500'))

    def test_exception_convert_to_message(self):
        ex = VNXException(message=StrangeException())
        assert_that(str(ex), equal_to('strange exception'))
