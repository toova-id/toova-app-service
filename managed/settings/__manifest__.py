# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Managed Settings',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Single-tenant company, user, role, and access settings',
    'depends': ['core', 'customers', 'vendors', 'contact_persons', 'people', 'products'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/actions.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
