# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Managed Business Directory',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Canonical party identity, roles, addresses, and duplicate prevention',
    'depends': ['managed_core', 'contacts', 'l10n_id_efaktur_coretax'],
    'data': ['security/ir.model.access.csv', 'views/navigation.xml'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
