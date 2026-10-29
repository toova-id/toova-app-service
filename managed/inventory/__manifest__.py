# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Managed Inventory',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Managed delivery workflow over native stock operations',
    'depends': ['sales', 'settings'],
    'data': ['security/groups.xml', 'security/ir.model.access.csv', 'views/actions.xml'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
