# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountPartnerLedger(models.TransientModel):
    _inherit = 'account.report.partner.ledger'

    supplier_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='account_partner_ledger_supplier_rel',
        column1='wizard_id',
        column2='partner_id',
        string='Fournisseurs',
        domain=[('supplier_rank', '>', 0)],
    )
    customer_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='account_partner_ledger_customer_rel',
        column1='wizard_id',
        column2='partner_id',
        string='Clients',
        domain=[('customer_rank', '>', 0)],
    )

    account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='account_partner_ledger_account_rel',
        column1='wizard_id',
        column2='account_id',
        string='Comptes',
        domain=[('account_type', 'in', ['asset_receivable', 'liability_payable'])],
    )

    def pre_print_report(self, data):
        data = super().pre_print_report(data)
        data['form']['supplier_ids'] = self.supplier_ids.ids or []
        data['form']['customer_ids'] = self.customer_ids.ids or []
        data['form']['account_ids_filter'] = self.account_ids.ids or []
        return data


