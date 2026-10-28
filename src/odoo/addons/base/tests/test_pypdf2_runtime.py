import concurrent.futures
from unittest.mock import patch

from odoo.tests.common import BaseCase
from odoo.tools import _pypdf2


class TestPyPdf2Runtime(BaseCase):
    def test_initializes_once(self):
        import PyPDF2.filters

        original = PyPDF2.filters.decompress
        with patch.object(_pypdf2, '_patched', False):
            with concurrent.futures.ThreadPoolExecutor(8) as executor:
                list(executor.map(lambda _: _pypdf2.patch_pypdf2(), range(32)))
            patched = PyPDF2.filters.decompress
        PyPDF2.filters.decompress = original

        self.assertIsNot(patched, original)
        self.assertEqual(patched(__import__('zlib').compress(b'odoo')), b'odoo')
