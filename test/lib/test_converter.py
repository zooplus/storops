# coding=utf-8
from __future__ import unicode_literals

from unittest import TestCase

from hamcrest import assert_that, equal_to, none, has_items

from vnxCliApi.lib import converter

__author__ = 'Cedric Zhuang'


class ConverterTest(TestCase):
    def test_to_int_arr(self):
        ret = converter.to_int_arr('12, 0, 5, 12')
        assert_that(ret, equal_to([12, 0, 5, 12]))

    def test_to_int_arr_space(self):
        ret = converter.to_int_arr('62 63 306 324')
        assert_that(ret, equal_to([62, 63, 306, 324]))

    def test_to_int_arr_space_str(self):
        ret = converter.to_int_arr('Unbound')
        assert_that(ret, equal_to([]))

    def test_to_int_arr_empty_input(self):
        ret = converter.to_int_arr('')
        assert_that(ret, equal_to([]))

    def test_to_int_str_map(self):
        ret = converter.to_int_str_map(
            '62: RAID5 63: RAID5 306: RAID10 324: RAID5')
        assert_that(len(ret), equal_to(4))
        assert_that(ret[62], equal_to('RAID5'))
        assert_that(ret[306], equal_to('RAID10'))

    def test_to_int_str_map_na(self):
        ret = converter.to_int_str_map('N/A')
        assert_that(len(ret), equal_to(0))

    def test_to_int_int_map_unbound(self):
        ret = converter.to_int_int_map('Unbound')
        assert_that(len(ret), equal_to(0))

    def test_to_int_int_map(self):
        ret = converter.to_int_int_map('62: 92 63: 93 306: 94 324: 95')
        assert_that(len(ret), equal_to(4))
        assert_that(ret[62], equal_to(92))
        assert_that(ret[324], equal_to(95))

    def test_str_to_int_invalid_input(self):
        ret = converter.to_int_arr('12, abc, 12c')
        self.assertEqual([12], ret)

    def test_arr_to_str(self):
        ret = converter.arr_to_str([5, -12, 7.21])
        self.assertEqual('5,-12,7.21', ret)

    def test_arr_to_str_with_sep(self):
        ret = converter.arr_to_str(['a bc', 112], '|')
        self.assertEqual('a bc|112', ret)

    def test_to_str_arr(self):
        ret = converter.to_str_arr([5, -12, 7.21])
        self.assertEqual(['5', '-12', '7.21'], ret)

    def test_to_hlu_alu_map(self):
        output = """
                 HLU/ALU Pairs:

                 HLU Number     ALU Number
                 ----------     ----------
                    0               4
                    12              A1
                 """
        alu2hlu = converter.to_alu_hlu_map(output)
        self.assertEqual(0, alu2hlu[4])
        self.assertEqual(None, alu2hlu.get('A1', None))

    def test_to_disk_indices(self):
        output = """
        Disks:
        Bus 0 Enclosure 0 Disk 9
        Bus 1 Enclosure 0 Disk 12
        Bus 1 Enclosure 0 Disk 9
        """
        indices = converter.to_disk_indices(output)
        assert_that(indices, has_items('0_0_9', '1_0_12', '1_0_9'))

    def test_number_to_date_int(self):
        ret = converter.vnx_time_to_date(3623881621)
        assert_that(str(ret), equal_to('2015-11-02 01:47:01'))

    def test_number_to_date_float(self):
        ret = converter.vnx_time_to_date(3617925585.15)
        assert_that(str(ret), equal_to('2015-08-25 03:19:45.150000'))

    def test_float_normal(self):
        ret = converter.to_float('1234.5678')
        assert_that(ret, equal_to(1234.5678))

    def test_float_na(self):
        ret = converter.to_float('N/A')
        assert_that(ret, none())

    def test_int_normal(self):
        ret = converter.to_float('1234')
        assert_that(ret, equal_to(1234))

    def test_int_disabled(self):
        ret = converter.to_int('Disabled')
        assert_that(ret, none())
