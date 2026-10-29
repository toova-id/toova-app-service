# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import date_utils


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    managed_monthly_reset = fields.Boolean()

    def _create_date_range_seq(self, date):
        self.ensure_one()
        if not self.managed_monthly_reset:
            return super()._create_date_range_seq(date)
        date_from, date_to = date_utils.get_month(fields.Date.to_date(date))
        return self.env['ir.sequence.date_range'].sudo().create({
            'date_from': date_from,
            'date_to': date_to,
            'sequence_id': self.id,
        })

    def _next(self, sequence_date=None):
        if sequence_date and self.managed_monthly_reset:
            if getattr(sequence_date, 'tzinfo', None):
                sequence_date = sequence_date.replace(tzinfo=None)
            sequence_date = fields.Datetime.to_datetime(sequence_date)
            self = self.with_context(ir_sequence_date=sequence_date)
        return super()._next(sequence_date=sequence_date)
