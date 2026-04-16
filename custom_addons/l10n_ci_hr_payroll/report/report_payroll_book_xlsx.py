# -*- coding: utf-8 -*-

from odoo import models


class PayrollBookXlsx(models.AbstractModel):
    _name = 'report.l10n_ci_hr_payroll.report_payroll_book_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Grand Livre de Paie XLSX'

    def generate_xlsx_report(self, workbook, data, objs):
        # Formats
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center',
        })
        subtitle_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'center',
        })
        header_fmt = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center',
            'bg_color': '#003366', 'font_color': 'white',
            'border': 1, 'text_wrap': True,
        })
        num_fmt = workbook.add_format({
            'num_format': '#,##0', 'font_size': 9, 'border': 1,
        })
        text_fmt = workbook.add_format({
            'font_size': 9, 'border': 1,
        })
        total_fmt = workbook.add_format({
            'bold': True, 'num_format': '#,##0', 'font_size': 9,
            'border': 1, 'top': 2, 'bg_color': '#E8E8E8',
        })
        total_text_fmt = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center',
            'border': 1, 'top': 2, 'bg_color': '#E8E8E8',
        })

        sheet = workbook.add_worksheet('Grand Livre de Paie')
        sheet.set_landscape()
        sheet.set_paper(9)  # A4

        headers_fixed = ['N°', 'Matricule', 'Nom et Prénoms', 'Emploi']
        all_headers = headers_fixed + data['headers']
        nb_cols = len(all_headers)

        # Largeurs colonnes
        sheet.set_column(0, 0, 4)    # N°
        sheet.set_column(1, 1, 10)   # Matricule
        sheet.set_column(2, 2, 25)   # Nom
        sheet.set_column(3, 3, 15)   # Emploi
        sheet.set_column(4, nb_cols - 1, 12)  # Montants

        # Titre
        row = 0
        sheet.merge_range(row, 0, row, nb_cols - 1, data['company_name'], title_fmt)
        row += 1
        sheet.merge_range(row, 0, row, nb_cols - 1, 'GRAND LIVRE DE PAIE', subtitle_fmt)
        row += 1
        period = "Période du %s au %s" % (data['date_from'], data['date_to'])
        if data['department_name'] != 'Tous':
            period += " — Département : %s" % data['department_name']
        sheet.merge_range(row, 0, row, nb_cols - 1, period, subtitle_fmt)
        row += 2

        # En-têtes
        for col, h in enumerate(all_headers):
            sheet.write(row, col, h, header_fmt)
        row += 1

        # Données
        codes = data['codes']
        for r in data['rows']:
            sheet.write(row, 0, r['num'], text_fmt)
            sheet.write(row, 1, r['matricule'], text_fmt)
            sheet.write(row, 2, r['name'], text_fmt)
            sheet.write(row, 3, r['emploi'], text_fmt)
            for i, code in enumerate(codes):
                val = r.get(code, 0)
                sheet.write(row, 4 + i, abs(val) if val else 0, num_fmt)
            row += 1

        # Totaux
        sheet.merge_range(row, 0, row, 3, 'TOTAUX', total_text_fmt)
        for i, code in enumerate(codes):
            val = data['totals'].get(code, 0)
            sheet.write(row, 4 + i, abs(val) if val else 0, total_fmt)
        row += 2

        # Nombre d'employés
        sheet.write(row, 0, "Nombre d'employés : %d" % len(data['rows']))
