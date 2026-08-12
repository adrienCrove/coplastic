# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountReportPartnerLedger(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="coplastic_partner_ledger_partner_rel",
        column1="wizard_id",
        column2="partner_id",
        string="Partenaires",
        help="Laisser vide pour inclure tous les partenaires ayant des "
             "écritures. Sinon, le rapport est limité aux partenaires "
             "sélectionnés.",
    )

    @api.onchange("result_selection")
    def _onchange_result_selection_clear_partners(self):
        for wizard in self:
            if wizard.result_selection != "supplier":
                wizard.partner_ids = [(5, 0, 0)]

    def _print_report(self, data):
        partner_ids = self.partner_ids.ids if self.result_selection == "supplier" else []
        data["form"]["partner_ids"] = partner_ids
        return super()._print_report(data)
