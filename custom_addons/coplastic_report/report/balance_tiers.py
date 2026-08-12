# -*- coding: utf-8 -*-
from odoo import api, models

# Types de pièces considérées comme "factures d'avoir" (avoirs clients / fournisseurs)
REFUND_MOVE_TYPES = ('out_refund', 'in_refund')


class ReportBalanceTiers(models.AbstractModel):
    _name = 'report.coplastic_report.report_balance_tiers'
    _description = 'Balance des tiers'
    _inherit = 'report.base_accounting_kit.report_trial_balance'

    def _get_accounts(self, accounts, display_account):
        """Ajoute à chaque compte sa clé `id` (nécessaire au filtrage) et le
        montant des factures d'avoir (`facture_avoir`), calculé sur le même
        contexte (dates / état des écritures) que le reste de la balance."""
        account_res = super()._get_accounts(accounts, display_account)

        # Montant des avoirs par compte, même contexte que la balance
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        request = (
            "SELECT account_move_line.account_id AS id, "
            "COALESCE(SUM(CASE WHEN m.move_type IN %s "
            "THEN account_move_line.credit ELSE 0.0 END), 0.0) AS facture_avoir "
            "FROM " + tables + ", account_move AS m "
            "WHERE account_move_line.move_id = m.id "
            "AND account_move_line.account_id IN %s " + filters +
            " GROUP BY account_move_line.account_id")
        params = (REFUND_MOVE_TYPES, tuple(accounts.ids)) + tuple(where_params)
        self.env.cr.execute(request, params)
        fa_by_id = {r['id']: r['facture_avoir']
                    for r in self.env.cr.dictfetchall()}

        code_to_id = {a.code: a.id for a in accounts}
        for acc in account_res:
            acc_id = code_to_id.get(acc.get('code'))
            acc['id'] = acc_id
            acc['facture_avoir'] = fa_by_id.get(acc_id, 0.0)
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data=data)

        form = (data or {}).get('form', {})
        account_ids_filter = form.get('account_ids_filter', [])
        tiers_type = form.get('tiers_type', 'all')

        tiers_accounts = []
        for acc in res.get('Accounts', []):
            code = acc.get('code', '')
            if not code.startswith('4'):
                continue
            # Filtre Clients (41) / Fournisseurs (40)
            if tiers_type == 'client' and not code.startswith('41'):
                continue
            if tiers_type == 'supplier' and not code.startswith('40'):
                continue
            # Filtre comptes explicitement sélectionnés dans le wizard
            if account_ids_filter and acc.get('id') not in account_ids_filter:
                continue
            tiers_accounts.append(acc)

        mvt_debit = sum(a.get('debit', 0.0) for a in tiers_accounts)
        mvt_credit = sum(a.get('credit', 0.0) for a in tiers_accounts)
        facture_avoir = sum(a.get('facture_avoir', 0.0) for a in tiers_accounts)
        solde_debit = sum(a.get('solde_debit', 0.0) for a in tiers_accounts)
        solde_credit = sum(a.get('solde_credit', 0.0) for a in tiers_accounts)

        res['tiers_accounts'] = tiers_accounts
        res['tiers_type'] = tiers_type
        res['tiers_totals'] = {
            'mvt_debit': mvt_debit,
            'mvt_credit': mvt_credit,
            'facture_avoir': facture_avoir,
            'solde_debit': solde_debit,
            'solde_credit': solde_credit,
        }
        return res
