import os

__version__ = '0.0.1'


def version():
    build_number = os.environ.get('BUILD_NUMBER', None)
    ret = __version__
    if build_number is not None:
        ret = '{}.{}'.format(ret, build_number)
    return ret
