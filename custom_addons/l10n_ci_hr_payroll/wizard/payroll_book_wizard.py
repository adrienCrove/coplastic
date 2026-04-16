# -*- coding: utf-8 -*-

import io
import json
from datetime import date

from odoo import fields, models


class PayrollBookWizard(models.TransientModel):
    _name = 'l10n.ci.payroll.book.wizard'
    _description = 'Grand Livre de Paie'

    date_from = fields.Date(
        string="Du",
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="Au",
        required=True,
        default=fields.Date.context_today,
    )
    department_id = fields.Many2one(
        'hr.department',
        string="Département",
    )
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
    ], default='pdf', required=True, string="Format")

    # Codes des règles à afficher dans le rapport
    SALARY_CODES = [
        'CI_BASE', 'CI_SURS', 'CI_BRUT_TOTAL',
        'CI_RET_SAL', 'CI_ITS_NET', 'CI_CMU_SAL', 'CI_TOT_COT_SAL',
        'CI_TRANSP', 'CI_NET',
        'CI_RET_PAT', 'CI_IS_PAT', 'CI_ITS_PAT',
        'CI_TA', 'CI_FPC', 'CI_PF', 'CI_AT', 'CI_CMU_PAT',
    ]

    COLUMN_HEADERS = [
        'Sal. Base', 'Sursalaire', 'Total Brut',
        'CNPS', 'ITS Net', 'CMU', 'Tot. Ret.',
        'Transport', 'Net à Payer',
        'CNPS', 'IS', 'ITS',
        'TA', 'FPC', 'PF', 'AT', 'CMU',
    ]

    def _prepare_report_data(self):
        domain = [
            ('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from),
            ('state', '=', 'done'),
        ]
        if self.department_id:
            domain.append(('employee_id.department_id', '=', self.department_id.id))

        payslips = self.env['hr.payslip'].search(domain, order='employee_id')

        rows = []
        totals = {code: 0.0 for code in self.SALARY_CODES}

        for seq, slip in enumerate(payslips, 1):
            line_map = {l.code: l.total for l in slip.line_ids}
            emp = slip.employee_id
            row = {
                'num': seq,
                'matricule': emp.l10n_ci_matricule or '',
                'name': emp.name,
                'emploi': emp.job_id.name or emp.job_title or '',
            }
            for code in self.SALARY_CODES:
                val = line_map.get(code, 0.0)
                row[code] = val
                totals[code] += val
            rows.append(row)

        return {
            'date_from': self.date_from.strftime('%d/%m/%Y'),
            'date_to': self.date_to.strftime('%d/%m/%Y'),
            'company_name': self.env.company.name,
            'department_name': self.department_id.name if self.department_id else 'Tous',
            'headers': self.COLUMN_HEADERS,
            'codes': self.SALARY_CODES,
            'rows': rows,
            'totals': totals,
        }

    def action_print(self):
        data = self._prepare_report_data()
        if self.output_format == 'xlsx':
            return self.env.ref(
                'l10n_ci_hr_payroll.action_report_payroll_book_xlsx'
            ).report_action(self, data=data)
        return self.env.ref(
            'l10n_ci_hr_payroll.action_report_payroll_book_pdf'
        ).report_action(self, data=data)
