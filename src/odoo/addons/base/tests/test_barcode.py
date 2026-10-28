# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import concurrent.futures
from unittest.mock import patch

from odoo.addons.base.models import ir_actions_report
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import check_barcode_encoding, get_barcode_check_digit


class TestBarcodeRuntime(BaseCase):
    def test_initializes_once(self):
        calls = []

        class Drawing:
            def asString(self, format):
                return b'png'

        class TypeFace:
            def __init__(self, name):
                pass

            def findT1File(self):
                return True

        def create_barcode_drawing(*args, **kwargs):
            calls.append((args, kwargs))
            return Drawing()

        with patch('reportlab.graphics.barcode.createBarcodeDrawing', create_barcode_drawing), \
             patch('reportlab.pdfbase.pdfmetrics.TypeFace', TypeFace), \
             patch.object(ir_actions_report, '_BARCODE_DRAWING', None), \
             patch.object(ir_actions_report, '_DEFAULT_BARCODE_FONT', None):
            with concurrent.futures.ThreadPoolExecutor(8) as executor:
                runtimes = list(executor.map(lambda _: ir_actions_report._barcode_runtime(), range(32)))

        self.assertEqual(len(calls), 1)
        self.assertTrue(all(runtime[0] is create_barcode_drawing for runtime in runtimes))
        self.assertTrue(all(runtime[1] == 'Courier' for runtime in runtimes))


class TestWkhtmltopdfRuntime(BaseCase):
    def test_initializes_once(self):
        process = type('Process', (), {
            'communicate': lambda self: (b'wkhtmltopdf 0.12.6.1', b''),
        })()
        with patch.object(ir_actions_report.subprocess, 'Popen', return_value=process) as popen, \
             patch.object(ir_actions_report, 'wkhtmltopdf_state', None), \
             patch.object(ir_actions_report, 'wkhtmltopdf_dpi_zoom_ratio', False):
            with concurrent.futures.ThreadPoolExecutor(8) as executor:
                states = list(executor.map(lambda _: ir_actions_report._check_wkhtmltopdf(), range(32)))

        self.assertEqual(states, ['ok'] * 32)
        popen.assert_called_once()

class TestBarcode(TransactionCase):
    def test_barcode_check_digit(self):
        ean8 = "87111125"
        self.assertEqual(get_barcode_check_digit("0" * 10 + ean8), int(ean8[-1]))
        ean13 = "1234567891231"
        self.assertEqual(get_barcode_check_digit("0" * 5 + ean13), int(ean13[-1]))

    def test_barcode_encoding(self):
        self.assertTrue(check_barcode_encoding('20220006', 'ean8'))
        self.assertTrue(check_barcode_encoding('93855341', 'ean8'))
        self.assertTrue(check_barcode_encoding('2022071416014', 'ean13'))
        self.assertTrue(check_barcode_encoding('9745213796142', 'ean13'))

        self.assertFalse(check_barcode_encoding('2022a006', 'ean8'), 'should contains digits only')
        self.assertFalse(check_barcode_encoding('20220000', 'ean8'), 'incorrect check digit')
        self.assertFalse(check_barcode_encoding('93855341', 'ean13'), 'ean13 is a 13-digits barcode')
        self.assertFalse(check_barcode_encoding('9745213796142', 'ean8'), 'ean8 is a 8-digits barcode')
        self.assertFalse(check_barcode_encoding('9745213796148', 'ean13'), 'incorrect check digit')
        self.assertFalse(check_barcode_encoding('2022!71416014', 'ean13'), 'should contains digits only')
        self.assertFalse(check_barcode_encoding('0022071416014', 'ean13'), 'when starting with one zero, it indicates that a 12-digit UPC-A code follows')
