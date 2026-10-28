{
    'name': 'Managed Indonesia Regions',
    'version': '16.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Normalized Indonesian province, city, district, village, and postal data',
    'depends': ['base'],
    'data': ['security/ir.model.access.csv'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
