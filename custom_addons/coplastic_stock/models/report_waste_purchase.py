# -*- coding: utf-8 -*-

import base64
import os
from collections import OrderedDict

from odoo import api, models


class ReportWastePurchase(models.AbstractModel):
    _name = 'report.coplastic_stock.report_waste_purchase_document'
    _description = 'Grand Livre Achats PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        product_ids = data.get('product_ids', [])
        mode = data.get('mode', 'summary')

        lines = self.env['purchase.order.line'].search([
            ('order_id.state', 'in', ['purchase', 'done']),
            ('product_id', 'in', product_ids),
            ('date_planned', '>=', date_from),
            ('date_planned', '<=', date_to + ' 23:59:59'),
        ], order='date_planned asc, product_id asc')

        if mode == 'summary':
            rows = self._build_summary(lines)
        else:
            rows = self._build_detailed(lines)

        grand_total_qty = sum(r['qty'] for r in rows)
        grand_total_amount = sum(r['amount'] for r in rows)

        company = self.env.company
        logo = ''
        if company.logo_web:
            raw = company.logo_web
            b64 = raw.decode('ascii') if isinstance(raw, bytes) else raw
            logo = 'data:image/png;base64,' + b64

        return {
            'doc_ids': docids,
            'date_from': data.get('date_from_fmt', date_from),
            'date_to': data.get('date_to_fmt', date_to),
            'mode': mode,
            'rows': rows,
            'grand_total_qty': grand_total_qty,
            'grand_total_amount': grand_total_amount,
            'company': company,
            'logo': logo,
            'fmt': lambda v: '{:,.0f}'.format(v).replace(',', ' '),
        }

    def _build_summary(self, lines):
        """Mode résumé : 1 ligne par produit, qté et montant sommés."""
        grouped = OrderedDict()
        for line in lines:
            pid = line.product_id.id
            if pid not in grouped:
                grouped[pid] = {
                    'product': line.product_id.name,
                    'date': '',
                    'qty': 0.0,
                    'amount': 0.0,
                }
            grouped[pid]['qty'] += line.product_qty
            grouped[pid]['amount'] += line.product_qty * line.price_unit
        return list(grouped.values())

    def _build_detailed(self, lines):
        """Mode détaillé : 1 ligne par produit + date."""
        grouped = OrderedDict()
        for line in lines:
            date_key = line.date_planned.date()
            pid = line.product_id.id
            key = (pid, date_key)
            if key not in grouped:
                grouped[key] = {
                    'product': line.product_id.name,
                    'date': date_key.strftime('%d/%m/%Y'),
                    'qty': 0.0,
                    'amount': 0.0,
                }
            grouped[key]['qty'] += line.product_qty
            grouped[key]['amount'] += line.product_qty * line.price_unit
        return list(grouped.values())
