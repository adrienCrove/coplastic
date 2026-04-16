# -*- coding: utf-8 -*-

from collections import OrderedDict

from odoo import api, models


class ReportWastePurchase(models.AbstractModel):
    _name = 'report.coplastic_stock.report_waste_purchase_document'
    _description = 'Rapport PDF Achats par Produit'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        product_id = data.get('product_id')
        product_name = data.get('product_name')

        lines = self.env['purchase.order.line'].search([
            ('order_id.state', 'in', ['purchase', 'done']),
            ('product_id', '=', product_id),
            ('date_planned', '>=', date_from),
            ('date_planned', '<=', date_to + ' 23:59:59'),
        ], order='date_planned asc')

        # Regrouper par date + fournisseur → sommer les quantités
        grouped = OrderedDict()
        grand_total_qty = 0.0
        for line in lines:
            date_key = line.date_planned.date()
            partner_name = line.order_id.partner_id.name or ''
            key = (date_key, partner_name)
            if key not in grouped:
                grouped[key] = {
                    'date': date_key,
                    'partner': partner_name,
                    'qty': 0.0,
                }
            grouped[key]['qty'] += line.product_qty
            grand_total_qty += line.product_qty

        rows = list(grouped.values())

        return {
            'doc_ids': docids,
            'date_from': data.get('date_from_fmt', date_from),
            'date_to': data.get('date_to_fmt', date_to),
            'product_name': product_name,
            'rows': rows,
            'grand_total_qty': grand_total_qty,
            'company': self.env.company,
            'fmt': lambda v: '{:,.0f}'.format(v).replace(',', ' '),
        }
