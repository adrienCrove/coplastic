# -*- coding: utf-8 -*-

from datetime import datetime, time

from odoo import models


class StockValuationSummaryXlsx(models.AbstractModel):
    _name = "report.coplastic_stock_valuation_summary.summary_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Résumé valorisation de stock XLSX"

    def generate_xlsx_report(self, workbook, data, objs):
        wizard = objs[:1]
        methode = wizard.methode if wizard else "restant"
        perimetre = wizard.perimetre if wizard else "tous"
        date_to = wizard.date_to if wizard else None
        include_zero = wizard.include_zero if wizard else True

        domain = []

        # --- Filtre périmètre (catégorie de produit) ---
        cat_label = "Tous les produits"
        if perimetre in ("pf", "mp"):
            cat_name = "PRODUITS FINIS" if perimetre == "pf" else "MATIERES PREMIERES"
            cat = self.env["product.category"].search(
                [("name", "=", cat_name)], limit=1
            )
            if cat:
                domain.append(("product_id.categ_id", "child_of", cat.id))
            cat_label = cat_name

        # --- Méthode de calcul ---
        if methode == "cumul":
            if date_to:
                domain.append(
                    ("create_date", "<=", datetime.combine(date_to, time.max))
                )
            qty_field, val_field = "quantity", "value"
        else:  # restant
            qty_field, val_field = "remaining_qty", "remaining_value"

        groups = self.env["stock.valuation.layer"].read_group(
            domain=domain,
            fields=["%s:sum" % qty_field, "%s:sum" % val_field],
            groupby=["product_id"],
        )

        rows = []
        for g in groups:
            if not g.get("product_id"):
                continue
            product = self.env["product.product"].browse(g["product_id"][0])
            qty = g.get(qty_field) or 0.0
            val = g.get(val_field) or 0.0
            if not include_zero and abs(qty) < 1e-6 and abs(val) < 1e-6:
                continue
            rows.append((product, qty, val))

        rows.sort(key=lambda r: (r[0].display_name or "").lower())

        sheet = workbook.add_worksheet("Valorisation résumée")
        bold = workbook.add_format({"bold": True})
        sub = workbook.add_format({"italic": True, "font_color": "#555555"})
        header = workbook.add_format(
            {"bold": True, "bg_color": "#D9EAF7", "border": 1}
        )
        qty_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        money = workbook.add_format({"num_format": "#,##0", "border": 1})
        cell = workbook.add_format({"border": 1})
        total_lbl = workbook.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
        total_money = workbook.add_format(
            {"bold": True, "bg_color": "#F2F2F2", "num_format": "#,##0", "border": 1}
        )
        total_qty = workbook.add_format(
            {"bold": True, "bg_color": "#F2F2F2", "num_format": "#,##0.00", "border": 1}
        )

        row = 0
        sheet.write(row, 0, "Valorisation résumée du stock", bold)
        row += 1
        if methode == "cumul":
            meth_txt = "Méthode : cumul des mouvements"
            if date_to:
                meth_txt += " au %s" % date_to.strftime("%d/%m/%Y")
        else:
            meth_txt = "Méthode : stock restant actuel (aujourd'hui)"
        sheet.write(row, 0, "%s  —  %s" % (meth_txt, cat_label), sub)
        row += 2

        columns = ["Produit", "Unité de mesure", "Quantité en stock", "Valeur du stock"]
        for col, label in enumerate(columns):
            sheet.write(row, col, label, header)
        row += 1

        total_val = 0.0
        for product, qty, val in rows:
            sheet.write(row, 0, product.display_name or "", cell)
            sheet.write(row, 1, product.uom_id.name or "", cell)
            sheet.write_number(row, 2, float(qty), qty_fmt)
            sheet.write_number(row, 3, float(val), money)
            total_val += float(val)
            row += 1

        sheet.write(row, 0, "TOTAL", total_lbl)
        sheet.write(row, 1, "", total_lbl)
        sheet.write(row, 2, "", total_qty)
        sheet.write_number(row, 3, total_val, total_money)

        sheet.set_column(0, 0, 40)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 18)
        sheet.set_column(3, 3, 18)
