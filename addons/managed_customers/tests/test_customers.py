from odoo.tests.common import TransactionCase


class TestManagedCustomers(TransactionCase):
    def test_customer_action_contract(self):
        contract = self.env['res.partner']._managed_ui_contract('managed_customers.action_customers')
        self.assertEqual(contract['list']['title'], 'Customers')
        fields = {field['name']: field for field in contract['form']['fields']}
        self.assertEqual(fields['managed_address_ids']['widget'], 'managed_addresses')
        self.assertEqual(fields['child_ids']['widget'], 'managed_contacts')

    def test_default_customer_addresses_feed_odoo(self):
        customer = self.env['res.partner'].create({'name': 'PT Address Test', 'is_company': True})
        billing = self.env['managed.partner.address'].create({
            'account_id': customer.id,
            'label': 'Finance',
            'recipient_name': 'Finance Team',
            'street': 'Billing Street 1',
            'use_for_billing': True,
            'is_default_billing': True,
        })
        shipping = self.env['managed.partner.address'].create({
            'account_id': customer.id,
            'label': 'Warehouse',
            'recipient_name': 'Warehouse Team',
            'street': 'Shipping Street 1',
            'use_for_shipping': True,
            'is_default_shipping': True,
        })
        addresses = customer.address_get(['invoice', 'delivery'])
        self.assertEqual(addresses['invoice'], billing.address_partner_id.id)
        self.assertEqual(addresses['delivery'], shipping.address_partner_id.id)
        self.assertEqual(shipping.address_partner_id.parent_id, customer)
        self.assertEqual(shipping.address_partner_id.type, 'delivery')

    def test_customer_pic_gets_contact_role_not_customer_role(self):
        customer = self.env['res.partner'].with_context(managed_party_role='customer').create({
            'name': 'PT Contact Role Test',
            'child_ids': [(0, 0, {'name': 'Managed PIC', 'type': 'contact'})],
        })
        pic = customer.child_ids.filtered(lambda partner: partner.name == 'Managed PIC')
        self.assertEqual(customer.managed_role_ids.role, 'customer')
        self.assertEqual(pic.managed_role_ids.role, 'contact')

    def test_latest_default_replaces_previous_default(self):
        customer = self.env['res.partner'].create({'name': 'PT Default Test', 'is_company': True})
        first = self.env['managed.partner.address'].create({
            'account_id': customer.id, 'label': 'First', 'recipient_name': 'First',
            'use_for_shipping': True, 'is_default_shipping': True,
        })
        second = self.env['managed.partner.address'].create({
            'account_id': customer.id, 'label': 'Second', 'recipient_name': 'Second',
            'use_for_shipping': True, 'is_default_shipping': True,
        })
        self.assertFalse(first.is_default_shipping)
        self.assertTrue(second.is_default_shipping)
