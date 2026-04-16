# -*- coding: utf-8 -*-

from odoo import api, models


# Comptes à masquer dans les rapports comptables PDF
# (comptes de transit Odoo, pas pertinents pour les états financiers)
HIDDEN_ACCOUNT_CODES = ['521004']


def _filter_hidden_accounts(result):
    """Filtre les comptes masqués dans les résultats de rapport."""
    if result.get('Accounts'):
        result['Accounts'] = [
            acc for acc in result['Accounts']
            if acc.get('code') not in HIDDEN_ACCOUNT_CODES
        ]
    return result


class ReportTrialBalance(models.AbstractModel):
    _inherit = 'report.base_accounting_kit.report_trial_balance'

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data=data)
        return _filter_hidden_accounts(res)


class ReportGeneralLedger(models.AbstractModel):
    _inherit = 'report.base_accounting_kit.report_general_ledger'

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data=data)
        return _filter_hidden_accounts(res)


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.base_accounting_kit.report_cash_flow'

    def get_account_lines(self, data):
        """Masque les comptes de transit dans le Bilan / Compte de résultat."""
        lines = super().get_account_lines(data)
        return [
            line for line in lines
            if not any(code in (line.get('name') or '') for code in HIDDEN_ACCOUNT_CODES)
        ]
