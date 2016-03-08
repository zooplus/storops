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

from unittest import TestCase

from hamcrest import equal_to, assert_that, not_none

from storops.vnx.enums import VNXSPEnum
from storops.vnx.parsers import VNXCliParser, VNXPropDescriptor, \
    VNXParserConfigFactory
from storops.vnx.resource import get_vnx_parser
from test.vnx.cli_mock import MockCli
from test.vnx.resource.fakes import STORAGE_GROUP_HBA

A = VNXPropDescriptor('-a', 'Prop A (name):', 'prop_a')
B = VNXPropDescriptor('-b', 'Prop B:')
C = VNXPropDescriptor('-c', 'Prop C:')
ID = VNXPropDescriptor(None, 'ID:', is_index=True)


class DemoParser(VNXCliParser):
    def __init__(self):
        super(DemoParser, self).__init__()
        self.add_property(A, B, C, ID)


class DemoParserNonIndex(VNXCliParser):
    def __init__(self):
        super(DemoParserNonIndex, self).__init__()
        self.add_property(VNXPropDescriptor('-b', 'Prop B:'))


class DemoParserRegexIndex(VNXCliParser):
    def __init__(self):
        super(DemoParserRegexIndex, self).__init__()
        self.add_property(
            VNXPropDescriptor(None,
                              r'\s*\w+:(\d+)',
                              'id',
                              is_index=True,
                              is_regex=True,
                              converter=int),
            VNXPropDescriptor(None,
                              r'\s*value:\s*(\w+)',
                              'value',
                              is_regex=True))


class DemoParserMultiIndices(VNXCliParser):
    def __init__(self):
        super(DemoParserMultiIndices, self).__init__()
        self.add_property(
            VNXPropDescriptor(None, 'A:', is_index=True),
            VNXPropDescriptor(None, 'B:', is_index=True),
            VNXPropDescriptor(None, 'C:'),
            VNXPropDescriptor(None, 'D:'))


class VNXCliParserTest(TestCase):
    def test_get_property_options(self):
        options = DemoParser().property_options
        self.assertEqual('-a -b -c', ' '.join(options))

    def test_get_index_descriptor(self):
        self.assertEqual('ID:',
                         DemoParser().index_property.label)

    def test_get_index_descriptor_none(self):
        self.assertIsNone(DemoParserNonIndex().index_property)

    def test_parse(self):
        output = """
                ID: test
                Prop A (Name): ab (c)
                Prop B: d ef
                """
        parser = DemoParser()
        parsed = parser.parse(output, [A, ID, C])

        self.assertEqual('ab (c)', parsed.prop_a)
        self.assertIsNone(parsed.prop_c)
        self.assertEqual('test', parsed.id)
        self.assertRaises(AttributeError, getattr, parsed, 'prop_b')

    def test_parse_empty_prop(self):
        output = """
                ID: test
                Prop A (Name): ab (c)
                Prop B:
                Prop C: abc
                """
        parser = DemoParser()
        parsed = parser.parse(output, [A, ID, B, C])

        assert_that(parsed.id, equal_to('test'))
        assert_that(parsed.prop_a, equal_to('ab (c)'))
        assert_that(parsed.prop_b, equal_to(''))

    def test_parse_regex_label(self):
        output = """
                id:123
                value:abcde
                id:456
                value:ghijk
                """
        parsed = DemoParserRegexIndex().parse_all(output)
        self.assertEqual(2, len(parsed))
        for i in parsed:
            if i.id == 123:
                assert_that(i.value, equal_to('abcde'))
            elif i.id == 456:
                assert_that(i.value, equal_to('ghijk'))
            else:
                self.fail('id not recognized.')

    def test_all_options(self):
        options = DemoParser().all_options
        assert_that(options, equal_to(['-a', '-b', '-c']))

    def test_parse_multi_index(self):
        output = """
        A: a0
        B: b0
        C: c0

        A: a0
        B: b0
        D: d0

        A: a0
        B: b1
        C: c1
        """
        parsed = DemoParserMultiIndices().parse_all(output)
        assert_that(len(parsed), equal_to(2))
        a0b0 = next(i for i in parsed if i.b == 'b0')
        assert_that(a0b0, not_none())
        assert_that(a0b0.a, equal_to('a0'))
        assert_that(a0b0.b, equal_to('b0'))
        assert_that(a0b0.c, equal_to('c0'))
        assert_that(a0b0.d, equal_to('d0'))

        a0b1 = next(i for i in parsed if i.b == 'b1')
        assert_that(a0b1, not_none())
        assert_that(a0b1.a, equal_to('a0'))
        assert_that(a0b1.b, equal_to('b1'))
        assert_that(a0b1.c, equal_to('c1'))


class VNXStorageGroupHBAParserTest(TestCase):
    def test_parse(self):
        data = get_vnx_parser("VNXStorageGroupHBA").parse(STORAGE_GROUP_HBA)
        self.assertEqual('abc.def.dev', data.host_name)
        self.assertEqual('A-3v1', data.sp_port)
        self.assertEqual('10.244.209.72', data.initiator_ip)
        self.assertEqual('1', data.tpgt)
        self.assertEqual('10000000000', data.isid)
        self.assertEqual(
            ('iqn.1991-05.com.microsoft:abc.def.dev',
             str(VNXSPEnum.SP_A), '3'), data.hba)

    def test_parse_no_header(self):
        output = """
                iqn.1991-05.com.microsoft:abc.def.dev  SP A     1
                Host name:             abc.def.dev
                SPPort:                A-1v0
                Initiator IP:          10.244.209.72
                TPGT:                  1
                ISID:                  10000000000
                """
        data = get_vnx_parser("VNXStorageGroupHBA").parse(output)
        self.assertEqual('abc.def.dev', data.host_name)
        self.assertEqual('A-1v0', data.sp_port)
        self.assertEqual('10.244.209.72', data.initiator_ip)
        self.assertEqual('1', data.tpgt)
        self.assertEqual('10000000000', data.isid)
        self.assertEqual(
            ('iqn.1991-05.com.microsoft:abc.def.dev', str(VNXSPEnum.SP_A),
             '1'), data.hba)


class VNXStorageGroupParserTest(TestCase):
    def test_parse(self):
        parser = get_vnx_parser('VNXStorageGroup')
        output = MockCli.read_file('storagegroup_-list_-host_-iscsiAttributes_'
                                   '-gname_microsoft.txt')
        sg = parser.parse(output)
        self.assertEqual(True, sg.shareable)
        self.assertEqual('microsoft', sg.name)
        self.assertEqual('12:34:56:78:9A:BC:DE:F1:23:45:67:89:AB:CD:EF:01',
                         sg.wwn)
        self.assertEqual(0, sg.alu_hlu_map[4])
        self.assertEqual(123, sg.alu_hlu_map[456])
        self.assertEqual(None, sg.alu_hlu_map.get(3, None))

        # assert for hba members
        self.assertEqual(3, len(sg.hba_sp_pairs))
        hba = sg.hba_sp_pairs[0]
        self.assertEqual('abc.def.dev', hba.host_name)


class VNXConsistencyGroupParserTest(TestCase):
    def test_parse(self):
        output = MockCli.read_file('snap_-group_-list_-detail.txt')
        parser = get_vnx_parser('VNXConsistencyGroup')
        cgs = parser.parse_all(output)
        cg = next(c for c in cgs if c.name == 'test cg name')
        assert_that(cg, not_none())
        self.assertEqual([1, 3], cg.lun_list)
        self.assertEqual('Ready', cg.state)

        cg = next(c for c in cgs if c.name == 'another cg')
        assert_that(cg, not_none())
        self.assertEqual([23, 24], cg.lun_list)
        self.assertEqual('Offline', cg.state)


class VNXPoolPropertiesTest(TestCase):
    def test_parse(self):
        output = MockCli.read_file('storagepool_-list_-all_-id_1.txt')
        parser = get_vnx_parser('VNXPool')
        pool = parser.parse(output)
        self.assertEqual('Ready', pool.state)
        self.assertEqual(1, pool.pool_id)
        self.assertEqual(2329.792, pool.user_capacity_gbs)
        self.assertEqual(1473.623, pool.available_capacity_gbs)
        self.assertEqual(None, pool.fast_cache)
        self.assertEqual('Pool_daq', pool.name)
        self.assertEqual(2701.767, pool.total_subscribed_capacity_gbs)
        self.assertEqual(70, pool.percent_full_threshold)


class VNXPoolFeatureParserTest(TestCase):
    # command:  storagepool -feature -info
    output = """
    Is Virtual Provisioning Supported:  true
    Max. Pools:  60
    Max. Disks Per Pool:  1496
    Max. Disks for all Pools:  1496
    Max. Disks Per Operation:  180
    Max. Pool LUNs:  4000
    Min. Pool LUN Size(Blocks):  1
    Max. Pool LUN Size(Blocks):  549755813888
    Max. Pool LUN Size(GBs):  262144.000
    Total Number of Pools:  2
    Total Number of Pool LUNs:  4
    Total Number of all Pool LUNs that are thin:  3
    Total Number of all Pool LUNs that are non-thin:  1
    Number of Disks used in Pools:  5
    Available Disks:
    Bus 0 Enclosure 0 Disk 24
    Bus 0 Enclosure 0 Disk 16
    Bus 0 Enclosure 0 Disk 5
    Bus 0 Enclosure 0 Disk 4
    """

    def test_parse(self):
        parser = get_vnx_parser('VNXPoolFeature')
        parsed = parser.parse(self.output)
        assert_that(parsed.max_pool_luns, equal_to(4000))
        assert_that(parsed.total_pool_luns, equal_to(4))


class VNXLunPropertiesTest(TestCase):
    def test_parse(self):
        output = MockCli.read_file('lun_-list_-all_-l_19.txt')
        parser = get_vnx_parser('VNXLun')
        parsed = parser.parse(output)
        wwn = '60:06:01:60:1A:50:35:00:CC:22:61:D6:76:B1:E4:11'
        self.assertEqual(wwn, parsed.wwn)
        self.assertEqual('test_lun', parsed.name)
        self.assertEqual(19, parsed.lun_id)
        self.assertEqual(1.0, parsed.total_capacity_gb)
        self.assertEqual(True, parsed.is_thin_lun)
        self.assertEqual(False, parsed.is_compressed)
        self.assertEqual(False, parsed.is_dedup)
        self.assertEqual('No Movement', parsed.tiering_policy)
        self.assertEqual('Optimize Pool', parsed.initial_tier)
        self.assertEqual('Ready', parsed.state)
        self.assertEqual('OK(0x0)', parsed.status)
        self.assertEqual('None', parsed.operation)
        self.assertEqual(VNXSPEnum.SP_A, parsed.current_owner)
        self.assertEqual('N/A', parsed.attached_snapshot)


class VNXParserConfigFactoryTest(TestCase):
    def test_read_properties(self):
        name = 'VNXConsistencyGroup'
        prop = get_vnx_parser(name)
        assert_that(prop.resource_name, equal_to(name))
        assert_that(prop.data_src, equal_to('cli'))

    def test_properties_sequence_should_align_with_file(self):
        props = get_vnx_parser('VNXSystem')
        assert_that(props.MODEL.sequence, equal_to(0))
        assert_that(props.NAME.sequence, equal_to(5))

    def test_get_rsc_pkg_name(self):
        name = VNXParserConfigFactory.get_rsc_pkg_name()
        assert_that(name, equal_to('storops.vnx.resource'))
