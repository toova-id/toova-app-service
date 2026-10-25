# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Managed Products',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Managed product catalog, identity rules, and UI contract',
    'depends': ['managed_directory', 'stock', 'l10n_id_efaktur_coretax'],
    'data': ['security/ir.model.access.csv', 'data/uom_data.xml', 'views/actions.xml'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
