# coding=utf-8
from __future__ import unicode_literals
from unittest import TestCase
import six
from hamcrest import assert_that
from hamcrest import equal_to
from vnxCliApi.enums import VNXError, VNXProvisionEnum, \
    VNXTieringEnum, VNXSPEnum, has_error


class VNXErrorTest(TestCase):
    def test_has_error(self):
        output = "The specified snapshot name is already in use. (0x716d8005)"
        self.assertTrue(has_error(output))

    def test_has_error_with_specific_error(self):
        output = "The specified snapshot name is already in use. (0x716d8005)"
        err = has_error(output, VNXError.SNAP_NAME_EXISTED)
        self.assertTrue(err)
        err = has_error(output, VNXError.LUN_ALREADY_EXPANDED)
        self.assertFalse(err)

    def test_has_error_not_found(self):
        output = "Cannot find the consistency group."
        err = has_error(output)
        self.assertTrue(err)

        err = has_error(output, VNXError.GENERAL_NOT_FOUND)
        self.assertTrue(err)

    def test_has_error_not_exist(self):
        output = "The specified snapshot does not exist."
        err = has_error(output, VNXError.GENERAL_NOT_FOUND)
        self.assertTrue(err)

        output = "The (pool lun) may not exist."
        err = has_error(output, VNXError.GENERAL_NOT_FOUND)
        self.assertTrue(err)

    def test_has_error_multi_line(self):
        output = """Could not retrieve the specified (pool lun).
                    The (pool lun) may not exist."""
        err = has_error(output, VNXError.GENERAL_NOT_FOUND)
        self.assertTrue(err)

    def test_has_error_regular_string_false(self):
        output = "Cannot unbind LUN because it's contained in a Storage Group."
        err = has_error(output, VNXError.GENERAL_NOT_FOUND)
        self.assertFalse(err)

    def test_has_error_multi_errors(self):
        output = "Cannot unbind LUN because it's contained in a Storage Group."
        err = has_error(output,
                        VNXError.LUN_IN_SG,
                        VNXError.GENERAL_NOT_FOUND)
        self.assertTrue(err)

        output = "Cannot unbind LUN because it's contained in a Storage Group."
        err = has_error(output,
                        VNXError.LUN_ALREADY_EXPANDED,
                        VNXError.LUN_NOT_MIGRATING)
        self.assertFalse(err)

    def test_has_error_ev_error(self):
        class ForTest(object):
            pass

        error = ForTest()
        error.where = 'EV_ScsiPipe::_sendCommand() - Sense Data'
        error.why = 'SP A: LUN already exists in the specified storage group.'
        error.who = '@(#)libconnect Revision 7.33.6.2.50 on 1/6/2015 21:54:55'

        err = has_error(error,
                        VNXError.SG_LUN_ALREADY_EXISTS)
        self.assertTrue(err)

    def test_sp_error_not_supported(self):
        out = ('Error returned from the target: 10.244.211.32\n'
               'CLI commands are not supported by the target storage system.')
        err = has_error(out, VNXError.SP_NOT_AVAILABLE)
        assert_that(err, equal_to(True))

    def test_sp_error_time_out(self):
        out = ("A network error occurred while "
               "trying to connect: '10.244.211.33'.\n"
               "Message : select: The connect timed out.")
        err = has_error(out, VNXError.SP_NOT_AVAILABLE)
        assert_that(err, equal_to(True))


class VNXProvisionEnumTest(TestCase):
    def test_get_opt_dedup(self):
        opt = VNXProvisionEnum.get_opt(VNXProvisionEnum.DEDUPED)
        self.assertEqual('-type Thin -deduplication on',
                         ' '.join(opt))

    def test_get_opt_thin(self):
        opt = VNXProvisionEnum.get_opt(VNXProvisionEnum.THIN)
        self.assertEqual('-type Thin',
                         ' '.join(opt))

    def test_get_opt_thick(self):
        opt = VNXProvisionEnum.get_opt(VNXProvisionEnum.THICK)
        self.assertEqual('-type NonThin',
                         ' '.join(opt))

    def test_get_opt_compressed(self):
        opt = VNXProvisionEnum.get_opt(VNXProvisionEnum.COMPRESSED)
        self.assertEqual('-type Thin',
                         ' '.join(opt))

    def test_get_opt_not_available(self):
        self.assertRaises(ValueError, VNXProvisionEnum.get_opt, 'na')


class VNXTieringEnumTest(TestCase):
    def test_get_opt(self):
        opt = VNXTieringEnum.get_opt(VNXTieringEnum.HIGH_AUTO)
        self.assertEqual(
            '-initialTier highestAvailable -tieringPolicy autoTier',
            ' '.join(opt))

    def test_get_opt_not_available(self):
        self.assertRaises(ValueError, VNXTieringEnum.get_opt, 'na')


class VNXSPEnumTest(TestCase):
    def test_from_str(self):
        data = {
            'spa': VNXSPEnum.SP_A,
            'sp': None,
            'sp_a': VNXSPEnum.SP_A,
            'SP b': VNXSPEnum.SP_B,
            'a': VNXSPEnum.SP_A,
            'b': VNXSPEnum.SP_B,
            'cs': VNXSPEnum.CONTROL_STATION,
            'Celerra_CS0_21111': VNXSPEnum.CONTROL_STATION,
            'VPI-24092B': VNXSPEnum.SP_B
        }

        for k, v in six.iteritems(data):
            assert_that(VNXSPEnum.from_str(k), equal_to(v),
                        'input: {}'.format(k))
