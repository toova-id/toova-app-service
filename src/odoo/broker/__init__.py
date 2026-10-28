# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .api import handler, publish, registered_handlers

__all__ = ['BrokerServer', 'handler', 'publish', 'registered_handlers']


def __getattr__(name):
    if name == 'BrokerServer':
        from .service import BrokerServer
        return BrokerServer
    raise AttributeError(name)
