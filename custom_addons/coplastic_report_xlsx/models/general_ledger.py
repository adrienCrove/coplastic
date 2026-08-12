# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang


class AccountReportGeneralLedgerXlsx(models.TransientModel):
    _inherit = "account.report.general.ledger"

    def check_report_xlsx(self):
        self.ensure_one()
        data = {}
        data["ids"] = self.env.context.get("active_ids", [])
        data["model"] = self.env.context.get("active_model", "ir.ui.menu")
        data["form"] = self.read(
            ["date_from", "date_to", "journal_ids", "target_move", "company_id"]
        )[0]
        used_context = self._build_contexts(data)
        data["form"]["used_context"] = dict(used_context, lang=get_lang(self.env).code)
        data = self.pre_print_report(data)
        data["form"].update(self.read(["initial_balance", "sortby"])[0])
        if data["form"].get("initial_balance") and not data["form"].get("date_from"):
            raise UserError(_("You must define a Start Date"))
        return self.with_context(discard_logo_check=True).env.ref(
            "coplastic_report_xlsx.action_report_general_ledger_xlsx"
        ).report_action(self, data=data)
