# -*- coding: utf-8 -*-

from odoo import models


class PartnerLedgerXlsx(models.AbstractModel):
    _name = "report.coplastic_report_xlsx.report_partner_ledger_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Partner Ledger XLSX"

    def generate_xlsx_report(self, workbook, data, objs):
        report_values = self.env[
            "report.base_accounting_kit.report_partnerledger"
        ]._get_report_values(objs.ids, data=data)
        sheet = workbook.add_worksheet("Partner Ledger")
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})

        row = 0
        title = data["form"].get("name", "Partner Ledger Report")
        sheet.write(row, 0, title, bold)
        row += 2
        columns = [
            "Partner",
            "Date",
            "Journal",
            "Account",
            "Move",
            "Reference",
            "Label",
            "Debit",
            "Credit",
            "Facture avoir",
            "Progress",
        ]
        for col, label in enumerate(columns):
            sheet.write(row, col, label, header)
        row += 1

        partners = report_values.get("docs", [])
        lines_fn = report_values.get("lines")
        for partner in partners:
            sheet.write(row, 0, partner.display_name, bold)
            row += 1
            for line in lines_fn(report_values, partner):
                sheet.write(row, 0, partner.display_name)
                sheet.write(row, 1, str(line.get("date") or ""))
                sheet.write(row, 2, line.get("code") or "")
                sheet.write(row, 3, line.get("a_code") or "")
                sheet.write(row, 4, line.get("move_name") or "")
                sheet.write(row, 5, line.get("ref") or "")
                sheet.write(row, 6, line.get("displayed_name") or line.get("name") or "")
                sheet.write_number(row, 7, float(line.get("debit") or 0.0), money)
                sheet.write_number(row, 8, float(line.get("credit") or 0.0), money)
                sheet.write_number(row, 9, float(line.get("facture_avoir") or 0.0), money)
                sheet.write_number(row, 10, float(line.get("progress") or 0.0), money)
                row += 1
            row += 1

        grand_totals = report_values.get("grand_totals") or {}
        if grand_totals:
            sheet.write(row, 0, "Grand total", bold)
            sheet.write(row, 1, "", bold)
            sheet.write(row, 2, "", bold)
            sheet.write(row, 3, "", bold)
            sheet.write(row, 4, "", bold)
            sheet.write(row, 5, "", bold)
            sheet.write(row, 6, "", bold)
            sheet.write_number(row, 7, float(grand_totals.get("debit") or 0.0), money)
            sheet.write_number(row, 8, float(grand_totals.get("credit") or 0.0), money)
            sheet.write_number(row, 9, float(grand_totals.get("facture_avoir") or 0.0), money)
            sheet.write_number(row, 10, float(grand_totals.get("balance") or 0.0), money)

        sheet.set_column(0, 0, 28)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 6, 20)
        sheet.set_column(7, 10, 14)
