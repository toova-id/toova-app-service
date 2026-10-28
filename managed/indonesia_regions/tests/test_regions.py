from odoo.tests.common import TransactionCase


class TestManagedIndonesiaRegions(TransactionCase):
    def test_hierarchy_and_postal_code(self):
        village = self.env['managed.indonesia.region'].search([('code', '=', '32.73.01.1001')])
        self.assertEqual(village.name, 'Sukarasa')
        self.assertEqual(village.postal_code, '40152')
        self.assertEqual(village.parent_id.code, '32.73.01')
        self.assertEqual(village.state_id.code, 'JB')
