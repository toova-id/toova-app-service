# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Provider-neutral broker API used by engine and client addons."""
import re

_TOPIC_RE = re.compile(r'^[A-Za-z0-9._-]+$')
_HANDLERS = {}


def validate_topic(topic):
    if not isinstance(topic, str) or not topic or len(topic) > 128 or not _TOPIC_RE.fullmatch(topic):
        raise ValueError('broker topic must contain only letters, numbers, dot, underscore, or dash')
    return topic


def handler(topic):
    """Register one trusted Python handler for a logical topic.

    Handler signature: ``handler(env, message)``.
    """
    topic = validate_topic(topic)

    def decorate(function):
        if topic in _HANDLERS and _HANDLERS[topic] is not function:
            raise ValueError(f'broker handler already registered for {topic}')
        _HANDLERS[topic] = function
        return function

    return decorate


def registered_handlers():
    return dict(_HANDLERS)


def publish(env, topic, payload=None, *, record_ids=None, key=None, user_id=None, company_id=None):
    """Transactional ORM publish; creates outbox row in current transaction."""
    return env['broker.publisher'].publish(
        topic, payload or {}, record_ids=record_ids, key=key,
        user_id=user_id, company_id=company_id,
    )
