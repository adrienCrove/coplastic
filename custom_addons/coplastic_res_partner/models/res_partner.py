# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_monthly_count = fields.Integer(
        compute='_compute_sale_monthly_count',
        string="Commandes ce mois",
    )

    @api.depends_context('uid')
    def _compute_sale_monthly_count(self):
        today = fields.Date.today()
        first_day = today.replace(day=1)
        for partner in self:
            partner.sale_monthly_count = self.env['sale.order'].search_count([
                ('partner_id', 'child_of', partner.id),
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', first_day),
            ])

    def action_view_monthly_consumption(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f"Consommation — {self.name}",
            'res_model': 'sale.order',
            'view_mode': 'pivot,graph,list',
            'domain': [
                ('partner_id', 'child_of', self.id),
                ('state', 'in', ['sale', 'done']),
            ],
            'context': {
                'search_default_group_by_month': 1,
                'group_by': ['date_order:month'],
                'measures': ['amount_total'],
                'pivot_measures': ['amount_total'],
                'pivot_row_groupby': ['date_order:month'],
            },
        }
