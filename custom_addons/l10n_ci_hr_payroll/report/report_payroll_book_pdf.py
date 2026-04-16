# -*- coding: utf-8 -*-

from odoo import api, models


class PayrollBookPdf(models.AbstractModel):
    _name = 'report.l10n_ci_hr_payroll.report_payroll_book'
    _description = 'Grand Livre de Paie PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        # data est déjà préparé par action_print() du wizard
        # On l'utilise directement car le wizard transient peut être nettoyé
        return {
            'doc_ids': docids,
            'docs': self.env['l10n.ci.payroll.book.wizard'].browse(docids),
            'data': data,
        }
