from odoo import fields, models


class ManagedIndonesiaRegion(models.Model):
    _name = 'managed.indonesia.region'
    _description = 'Indonesia Administrative Region'
    _order = 'code'
    _rec_name = 'name'

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, index=True)
    parent_id = fields.Many2one('managed.indonesia.region', ondelete='restrict', index=True)
    level = fields.Selection([
        ('province', 'Province'),
        ('regency', 'Regency/City'),
        ('district', 'District'),
        ('village', 'Village'),
    ], required=True, index=True)
    postal_code = fields.Char(index=True)
    state_id = fields.Many2one('res.country.state', ondelete='restrict', index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('managed_indonesia_region_code_unique', 'unique(code)', 'Region code must be unique.'),
    ]

    def name_get(self):
        return [(region.id, region.name) for region in self]
