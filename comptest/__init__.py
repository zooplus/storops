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

import filelock

from comptest.utils import setup_log
from storops import VNXSystem, UnitySystem, cache

__author__ = 'Cedric Zhuang'

log = logging.getLogger(__name__)


@cache
def t_vnx():
    _lock = filelock.FileLock('init_t_vnx.lck')
    with _lock.acquire():
        vnx = VNXSystem('10.244.211.30', 'sysadmin', 'sysadmin')
        log.debug('initialize vnx system: {}'.format(vnx.existed))
    return vnx


@cache
def t_unity():
    return UnitySystem('10.244.223.66', 'admin', 'Password123!')


setup_log()
