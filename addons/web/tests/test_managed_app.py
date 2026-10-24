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
        self.assertIn('/app-assets/assets/app.js', app.text)
        asset = self.url_open('/app-assets/assets/app.js')
        self.assertEqual(asset.status_code, 200)
        self.assertEqual(asset.headers['Cache-Control'], 'no-store, max-age=0')

        session = self.url_open('/api/v1/session')
        self.assertEqual(session.status_code, 200)
        payload = session.json()
        self.assertEqual(payload['user']['id'], self.user.id)
        self.assertEqual(payload['company']['id'], self.user.company_id.id)
        self.assertIn('web', payload['modules'])

        navigation = self.url_open('/api/v1/ui/navigation')
        self.assertEqual(navigation.status_code, 200)
        items = navigation.json()['items']
        self.assertIsInstance(items, list)
        self.assertNotIn('Apps', {item['label'] for item in items})
        self.assertNotIn('Settings', {item['label'] for item in items})
        paths = [item['path'] for item in items if item['path']]
        self.assertTrue(all(path.startswith('/app/') for path in paths))
        self.assertTrue(all('ir.actions.' not in path for path in paths))
        self.assertTrue(all('xmlid' in item and 'module' in item for item in items))
