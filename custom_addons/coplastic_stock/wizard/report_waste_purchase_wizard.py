# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models


class ReportWastePurchaseWizard(models.TransientModel):
    _name = 'report.waste.purchase.wizard'
    _description = 'Assistant Grand Livre Achats'

    date_from = fields.Date(
        string='Du',
        required=True,
        default=lambda self: self._default_date_from(),
    )
    date_to = fields.Date(
        string='Au',
        required=True,
        default=lambda self: self._default_date_to(),
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Produits',
        required=True,
    )

    mode = fields.Selection([
        ('summary', 'Résumé (1 ligne par produit)'),
        ('detailed', 'Détaillé (1 ligne par produit / date)'),
    ], string='Mode', default='summary', required=True)

    @api.model
    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today - datetime.timedelta(days=today.weekday())

    @api.model
    def _default_date_to(self):
        today = fields.Date.context_today(self)
        monday = today - datetime.timedelta(days=today.weekday())
        return monday + datetime.timedelta(days=4)

    def action_print(self):
        data = {
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
            'date_from_fmt': self.date_from.strftime('%d/%m/%Y'),
            'date_to_fmt': self.date_to.strftime('%d/%m/%Y'),
            'product_ids': self.product_ids.ids,
            'mode': self.mode,
        }
        return self.env.ref(
            'coplastic_stock.action_report_waste_purchase'
        ).report_action(self, data=data)
