# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    reconciled_payment_ids = fields.Many2many(
        'account.payment',
        compute='_compute_reconciled_payment_ids',
        string="Paiements rapprochés",
    )
    reconciled_payment_count = fields.Integer(
        compute='_compute_reconciled_payment_ids',
        string="Nombre de paiements",
    )

    @api.depends('line_ids.matched_debit_ids', 'line_ids.matched_credit_ids')
    def _compute_reconciled_payment_ids(self):
        for move in self:
            payments = move._get_reconciled_payments()
            move.reconciled_payment_ids = payments
            move.reconciled_payment_count = len(payments)

    def action_open_payments(self):
        """Smart button : ouvre les paiements liés à la facture."""
        self.ensure_one()
        payments = self.reconciled_payment_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _("Paiements"),
            'res_model': 'account.payment',
            'domain': [('id', 'in', payments.ids)],
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action['view_mode'] = 'list,form'
        return action
