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

import logging
from logging.handlers import RotatingFileHandler
import os
from os.path import join, dirname, abspath

import sys

import errno

from storops import VNXSystem, UnitySystem, cache

__author__ = 'Cedric Zhuang'


@cache
def t_vnx():
    return VNXSystem('10.244.211.30', 'sysadmin', 'sysadmin')


@cache
def t_unity():
    return UnitySystem('10.244.223.66', 'admin', 'Password123!')


def log_folder():
    folder = join(dirname(abspath(__file__)), '..', 'logs')
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise
    return folder


def setup_log():
    fmt_str = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
    level = logging.DEBUG
    filename = join(log_folder(), 'comp_test.log')

    root = logging.getLogger()
    root.setLevel(level)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(fmt_str))

    fh = RotatingFileHandler(filename, maxBytes=10 * 1024 ** 2, backupCount=20)
    fh.setFormatter(logging.Formatter(fmt_str))

    root.addHandler(ch)
    root.addHandler(fh)


setup_log()
