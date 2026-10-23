# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user


class TestManagedSaleApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            'managed_sale_user',
            password='managed_sale_user',
            groups='sales_team.group_sale_salesman',
        )
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.env['res.partner'].create({'name': 'Managed API Customer'}).id,
            'user_id': cls.user.id,
        })

    def test_order_list_respects_user_access(self):
        self.authenticate(self.user.login, 'managed_sale_user')
        response = self.url_open('/api/v1/sales/orders?q=Managed')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['items'][0]['id'], self.order.id)
        self.assertEqual(payload['items'][0]['customer'], 'Managed API Customer')

    def test_invalid_page(self):
        self.authenticate(self.user.login, 'managed_sale_user')
        response = self.url_open('/api/v1/sales/orders?page=invalid')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'invalid_page')
