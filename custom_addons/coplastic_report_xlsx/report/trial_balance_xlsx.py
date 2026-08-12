# -*- coding: utf-8 -*-

from odoo import models


class TrialBalanceXlsx(models.AbstractModel):
    _name = "report.coplastic_report_xlsx.report_trial_balance_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Trial Balance XLSX"

    def generate_xlsx_report(self, workbook, data, objs):
        report_values = self.env[
            "report.base_accounting_kit.report_trial_balance"
        ]._get_report_values(objs.ids, data=data)
        sheet = workbook.add_worksheet("Trial Balance")
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})

        row = 0
        title = data["form"].get("name", "Trial Balance")
        sheet.write(row, 0, title, bold)
        row += 2
        columns = ["Account Code", "Account Name", "Debit", "Credit", "Balance"]
        for col, label in enumerate(columns):
            sheet.write(row, col, label, header)
        row += 1

        for account in report_values.get("Accounts", []):
            sheet.write(row, 0, account.get("code") or "")
            sheet.write(row, 1, account.get("name") or "")
            sheet.write_number(row, 2, float(account.get("debit") or 0.0), money)
            sheet.write_number(row, 3, float(account.get("credit") or 0.0), money)
            sheet.write_number(row, 4, float(account.get("balance") or 0.0), money)
            row += 1

        sheet.set_column(0, 0, 18)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 4, 16)
