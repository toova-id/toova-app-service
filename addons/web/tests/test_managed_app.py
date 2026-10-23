# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user


class TestManagedApp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'managed_app_user', password='managed_app_user')

    def test_app_and_session(self):
        self.authenticate(self.user.login, 'managed_app_user')

        app = self.url_open('/app')
        self.assertEqual(app.status_code, 200)
        self.assertIn('id="root"', app.text)
        self.assertIn('/web/static/app/assets/app-', app.text)

        session = self.url_open('/api/v1/session')
        self.assertEqual(session.status_code, 200)
        payload = session.json()
        self.assertEqual(payload['user']['id'], self.user.id)
        self.assertEqual(payload['company']['id'], self.user.company_id.id)
        self.assertIn('web', payload['modules'])
