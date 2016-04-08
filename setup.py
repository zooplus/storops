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
from setuptools import setup, find_packages
import io
import os

__author__ = 'Cedric Zhuang'

__version__ = '0.1.16'


def version():
    return __version__


def here(filename=None):
    ret = os.path.abspath(os.path.dirname(__file__))
    if filename is not None:
        ret = os.path.join(ret, filename)
    return ret


def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n\n')
    buf = []
    for filename in filenames:
        with io.open(here(filename), encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)


def read_requirements(filename):
    with open(filename) as f:
        return f.read().splitlines()


def get_description():
    return "VNX Python API."


def get_long_description():
    filename = 'README.md'
    try:
        import pypandoc
        ret = pypandoc.convert(filename, 'rst')
    except ImportError:
        ret = read(filename)
    return ret


setup(
    name="storops",
    version=version(),
    author="Cedric Zhuang",
    author_email="cedric.zhuang@gmail.com",
    description=get_description(),
    license="Apache Software License",
    keywords="VNX",
    include_package_data=True,
    packages=find_packages(),
    platforms=['any'],
    long_description=get_long_description(),
    classifiers=[
        "Programming Language :: Python",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=read_requirements('requirements.txt'),
    tests_require=read_requirements('test-requirements.txt')
)
