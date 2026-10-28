# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .nsq import NSQProvider


def get_provider(config):
    if config['broker_provider'] == 'nsq':
        return NSQProvider(config)
    raise ValueError(f"Unsupported broker provider: {config['broker_provider']}")
