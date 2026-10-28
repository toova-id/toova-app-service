# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user


class TestManagedUiApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'managed_ui_user', password='managed_ui_user')

    def test_visible_action_schema_and_records(self):
        self.authenticate(self.user.login, 'managed_ui_user')
        navigation = self.url_open('/api/v1/ui/navigation').json()['items']

        def find_action(items):
            for item in items:
                if item['actionId']:
                    return item['actionId']
                action_id = find_action(item['children'])
                if action_id:
                    return action_id

        action_id = find_action(navigation)
        self.assertTrue(action_id)
        schema = self.url_open(f'/api/v1/ui/actions/{action_id}')
        self.assertEqual(schema.status_code, 200)
        list_schema = schema.json()['list']
        self.assertTrue(list_schema['columns'])
        self.assertIn('filters', list_schema)
        self.assertIn('actions', list_schema)
        self.assertIn('export', list_schema)
        form_schema = schema.json()['form']
        self.assertIn('onchange', form_schema)
        self.assertIn('buttons', form_schema)
        self.assertIn('statusVisible', form_schema)

        records = self.url_open(f'/api/v1/ui/actions/{action_id}/records?page=1')
        self.assertEqual(records.status_code, 200)
        self.assertIn('items', records.json())

    def test_hidden_action_rejected(self):
        self.authenticate(self.user.login, 'managed_ui_user')
        response = self.url_open('/api/v1/ui/actions/999999')
        self.assertEqual(response.status_code, 403)

    def test_unmanaged_native_action_rejected(self):
        self.authenticate(self.user.login, 'managed_ui_user')
        action = self.env.ref('account.action_move_out_invoice_type', raise_if_not_found=False)
        if action:
            response = self.url_open(f'/api/v1/ui/actions/{action.id}')
            self.assertEqual(response.status_code, 403)
