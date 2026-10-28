# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import MagicMock, patch

from odoo.http import RedisSessionStore, Session
from odoo.tests.common import BaseCase


class TestRedisSessionStore(BaseCase):

    def test_roundtrip_and_delete(self):
        redis = MagicMock()
        values = {}
        redis.setex.side_effect = lambda key, ttl, value: values.__setitem__(key, value)
        redis.get.side_effect = lambda key: values.get(key)
        redis.delete.side_effect = lambda key: values.pop(key, None)
        with patch('redis.Redis.from_url', return_value=redis):
            store = RedisSessionStore('redis://test', 'test:', session_class=Session)
        session = store.new()
        session['uid'] = 7
        store.save(session)
        self.assertEqual(store.get(session.sid).uid, 7)
        store.delete(session)
        self.assertTrue(store.get(session.sid).is_new)
