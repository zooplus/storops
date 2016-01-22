# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to, raises

from test.vnx.cli_mock import patch_cli, t_cli
from vnxCliApi.exception import VNXSnapError
from vnxCliApi.vnx.resource.snap import VNXSnap

__author__ = 'Cedric Zhuang'


class VNXSnapTest(TestCase):
    @patch_cli()
    def test_properties(self):
        snap = VNXSnap('gan_snap', t_cli())
        assert_that(snap.name, equal_to('gan_snap'))
        assert_that(snap.description, equal_to('gan snap'))
        assert_that(snap.creation_time, equal_to('05/24/13 20:06:12'))
        assert_that(snap.last_modify_time, equal_to('07/23/14 12:28:42'))
        assert_that(snap.last_modified_by, equal_to('N/A'))
        assert_that(snap.source_luns, equal_to([57]))
        assert_that(snap.source_cg, equal_to('N/A'))
        assert_that(snap.primary_luns, equal_to([57]))
        assert_that(snap.state, equal_to('Ready'))
        assert_that(snap.status, equal_to('OK(0x0)'))
        assert_that(snap.allow_read_write, equal_to(True))
        assert_that(snap.modified, equal_to(True))
        assert_that(snap.attached_luns, equal_to([]))
        assert_that(snap.allow_auto_delete, equal_to(True))
        assert_that(snap.expiration_date, equal_to('Never'))
        assert_that(snap.existed, equal_to(True))

    @patch_cli()
    def test_get_all(self):
        snaps = VNXSnap.get(t_cli())
        assert_that(len(snaps), equal_to(47))

    @patch_cli()
    def test_get_by_name(self):
        snap = VNXSnap.get(t_cli(), name='gan_snap')
        assert_that(snap.creation_time, equal_to('05/24/13 20:06:12'))

    @patch_cli(output='snap_-list_-detail_error.txt')
    def test_get_not_found(self):
        snap = VNXSnap.get(t_cli(), name='xxx')
        assert_that(snap.existed, equal_to(False))

    @patch_cli()
    def test_copy_snap(self):
        def f():
            src = VNXSnap.get(t_cli(), name='123')
            src.copy('456')

        assert_that(f, raises(VNXSnapError, 'Cannot copy'))

    @patch_cli()
    def test_modify_snap(self):
        snap = VNXSnap(cli=t_cli(), name='s1')
        snap.modify(new_name='s2', rw=True)
        assert_that(snap._name, equal_to('s2'))

    @patch_cli()
    def test_modify_snap_failed(self):
        snap = VNXSnap(cli=t_cli(), name='s2')
        try:
            snap.modify(new_name='s1')
            self.fail('should have raise an exception.')
        except VNXSnapError:
            assert_that(snap._name, equal_to('s2'))
