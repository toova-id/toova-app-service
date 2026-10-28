# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Managed Sales',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Managed quotation and sales order workflow',
    'data': ['views/actions.xml'],
    'depends': ['sale_stock', 'contact_persons', 'products'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
