# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user


class TestManagedInbox(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'inbox_user', password='inbox_user')
        cls.channel = cls.env['mail.channel'].create({'name': 'Inbox Test', 'channel_type': 'channel'})
        cls.channel.add_members([cls.user.partner_id.id], post_joined_message=False)
        cls.channel.with_user(cls.user).message_post(body='Halo Inbox', message_type='comment', subtype_xmlid='mail.mt_comment')

    def test_inbox_membership_and_messages(self):
        self.authenticate(self.user.login, 'inbox_user')
        overview = self.url_open('/api/v1/inbox')
        self.assertEqual(overview.status_code, 200)
        self.assertIn(self.channel.id, [item['id'] for item in overview.json()['conversations']])
        thread = self.url_open(f'/api/v1/inbox/channels/{self.channel.id}')
        self.assertEqual(thread.status_code, 200)
        self.assertEqual(thread.json()['messages'][-1]['body'], '<p>Halo Inbox</p>')

    def test_non_member_cannot_read_channel(self):
        hidden = self.env['mail.channel'].create({'name': 'Hidden Inbox', 'channel_type': 'group'})
        self.authenticate(self.user.login, 'inbox_user')
        response = self.url_open(f'/api/v1/inbox/channels/{hidden.id}')
        self.assertEqual(response.status_code, 403)
