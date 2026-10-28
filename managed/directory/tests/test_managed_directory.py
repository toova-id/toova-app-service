# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManagedDirectory(TransactionCase):

    def test_identity_and_roles(self):
        indonesia = self.env.ref('base.id')
        partner = self.env['res.partner'].with_context(managed_ui=True, managed_party_role='customer').create({
            'name': 'First', 'country_id': indonesia.id, 'mobile': '0812-3456-7890', 'vat': '12.345.678.9-012.000',
        })
        self.assertEqual(partner.managed_phone_normalized, '6281234567890')
        self.assertEqual(partner.managed_vat_normalized, '123456789012000')
        self.assertEqual(partner.managed_role_ids.role, 'customer')
        with self.assertRaises(ValidationError):
            self.env['res.partner'].with_context(managed_ui=True).create({'name': 'Duplicate', 'vat': '123456789012000'})

    def test_foreign_phone_does_not_assume_indonesia(self):
        partner = self.env['res.partner'].create({'name': 'Foreign', 'mobile': '020 7946 0018'})
        self.assertEqual(partner.managed_phone_normalized, '02079460018')

    def test_main_address_text_maps_to_native_street_fields(self):
        partner = self.env['res.partner'].create({
            'name': 'Address Text', 'managed_address_text': 'Jalan Utama 1\nGedung B',
        })
        self.assertEqual(partner.street, 'Jalan Utama 1')
        self.assertEqual(partner.street2, 'Gedung B')
        partner.write({'managed_address_text': 'Alamat Baru'})
        self.assertEqual(partner.street, 'Alamat Baru')
        self.assertFalse(partner.street2)

    def test_indonesia_village_normalizes_city_state_and_postal_code(self):
        customer = self.env['res.partner'].create({'name': 'Region Customer'})
        village = self.env['managed.indonesia.region'].search([('code', '=', '32.73.01.1001')])
        address = self.env['managed.partner.address'].create({
            'account_id': customer.id, 'label': 'Bandung', 'recipient_name': 'Receiver',
            'country_id': self.env.ref('base.id').id,
            'indonesia_regency_id': village.parent_id.parent_id.id,
            'indonesia_district_id': village.parent_id.id,
            'indonesia_village_id': village.id,
        })
        self.assertEqual(address.address_partner_id.city, 'Kota Bandung')
        self.assertEqual(address.address_partner_id.state_id.code, 'JB')
        self.assertEqual(address.address_partner_id.zip, '40152')
