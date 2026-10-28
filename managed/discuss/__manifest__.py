# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Managed Inbox',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Managed team inbox, channels, direct messages, and activities',
    'depends': ['settings', 'mail'],
    'data': ['security/groups.xml', 'views/actions.xml'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
