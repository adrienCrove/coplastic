# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models


class ReportWastePurchaseWizard(models.TransientModel):
    _name = 'report.waste.purchase.wizard'
    _description = 'Assistant rapport achats par produit'

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
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True,
    )

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
            'product_id': self.product_id.id,
            'product_name': self.product_id.name,
        }
        return self.env.ref(
            'coplastic_stock.action_report_waste_purchase'
        ).report_action(self, data=data)
