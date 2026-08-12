# -*- coding: utf-8 -*-

from odoo import models


class GeneralLedgerXlsx(models.AbstractModel):
    _name = "report.coplastic_report_xlsx.report_general_ledger_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "General Ledger XLSX"

    def generate_xlsx_report(self, workbook, data, objs):
        report_values = self.env[
            "report.base_accounting_kit.report_general_ledger"
        ]._get_report_values(objs.ids, data=data)
        sheet = workbook.add_worksheet("General Ledger")
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})

        row = 0
        title = data["form"].get("name", "General Ledger")
        sheet.write(row, 0, title, bold)
        row += 2
        columns = [
            "Account",
            "Date",
            "Journal",
            "Partner",
            "Move",
            "Reference",
            "Label",
            "Debit",
            "Credit",
            "Balance",
        ]
        for col, label in enumerate(columns):
            sheet.write(row, col, label, header)
        row += 1

        for account in report_values.get("Accounts", []):
            sheet.write(row, 0, f"{account.get('code', '')} {account.get('name', '')}", bold)
            row += 1
            for line in account.get("move_lines", []):
                sheet.write(row, 0, account.get("code", ""))
                sheet.write(row, 1, str(line.get("ldate") or line.get("date") or ""))
                sheet.write(row, 2, line.get("lcode") or "")
                sheet.write(row, 3, line.get("partner_name") or "")
                sheet.write(row, 4, line.get("move_name") or "")
                sheet.write(row, 5, line.get("lref") or "")
                sheet.write(row, 6, line.get("lname") or "")
                sheet.write_number(row, 7, float(line.get("debit") or 0.0), money)
                sheet.write_number(row, 8, float(line.get("credit") or 0.0), money)
                sheet.write_number(row, 9, float(line.get("balance") or 0.0), money)
                row += 1
            sheet.write(row, 6, "Total", bold)
            sheet.write_number(row, 7, float(account.get("debit") or 0.0), money)
            sheet.write_number(row, 8, float(account.get("credit") or 0.0), money)
            sheet.write_number(row, 9, float(account.get("balance") or 0.0), money)
            row += 2

        sheet.set_column(0, 0, 28)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 6, 20)
        sheet.set_column(7, 9, 14)
