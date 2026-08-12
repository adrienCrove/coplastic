# -*- coding: utf-8 -*-
from odoo import api, models, _


class ReportTrialBalanceCoplastic(models.AbstractModel):
    _inherit = 'report.base_accounting_kit.report_trial_balance'

    _CLASS_LABELS = {
        '1': 'CLASSE 1 - RESSOURCES DURABLES',
        '2': 'CLASSE 2 - ACTIF IMMOBILISÉ',
        '3': 'CLASSE 3 - ACTIF CIRCULANT',
        '4': 'CLASSE 4 - TIERS',
        '5': 'CLASSE 5 - TRÉSORERIE',
        '6': 'CLASSE 6 - CHARGES',
        '7': 'CLASSE 7 - PRODUITS',
        '8': 'CLASSE 8 - AUTRES CHARGES ET PRODUITS',
    }

    # Comptes à exclure définitivement de la balance (comptes en suspens internes)
    _EXCLUDED_ACCOUNTS = {'521002'}

    def _get_accounts(self, accounts, display_account):
        account_res = super()._get_accounts(accounts, display_account)
        for acc in account_res:
            bal = acc.get('balance', 0.0)
            acc['solde_debit'] = bal if bal > 0 else 0.0
            acc['solde_credit'] = -bal if bal < 0 else 0.0
        account_res = [a for a in account_res
                       if a.get('code', '') not in self._EXCLUDED_ACCOUNTS]
        # if display_account == 'movement':
        #     account_res = [a for a in account_res
        #                    if a.get('solde_debit') or a.get('solde_credit')]
        return account_res

    def _empty_totals(self):
        return {'mvt_debit': 0.0, 'mvt_credit': 0.0,
                'solde_debit': 0.0, 'solde_credit': 0.0}

    def _add_to_totals(self, totals, acc):
        totals['mvt_debit'] += acc.get('debit', 0.0)
        totals['mvt_credit'] += acc.get('credit', 0.0)
        totals['solde_debit'] += acc.get('solde_debit', 0.0)
        totals['solde_credit'] += acc.get('solde_credit', 0.0)

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data)
        account_res = res['Accounts']

        # Recompute solde_debit/credit (parent may not have set them)
        for acc in account_res:
            if 'solde_debit' not in acc:
                bal = acc.get('balance', 0.0)
                acc['solde_debit'] = bal if bal > 0 else 0.0
                acc['solde_credit'] = -bal if bal < 0 else 0.0

        # Group by accounting class (first digit of code)
        classes_dict = {}
        for acc in account_res:
            cls = acc['code'][0] if acc.get('code') else '9'
            if cls not in classes_dict:
                classes_dict[cls] = {
                    'cls': cls,
                    'label': self._CLASS_LABELS.get(cls, f'CLASSE {cls}'),
                    'accounts': [],
                    **self._empty_totals(),
                }
            classes_dict[cls]['accounts'].append(acc)
            self._add_to_totals(classes_dict[cls], acc)

        classes_list = [classes_dict[k] for k in sorted(classes_dict.keys())]

        # Totaux comptes de bilan (classes 1-5)
        bilan = self._empty_totals()
        bilan['label'] = _('Totaux comptes de bilan')
        for k in ['1', '2', '3', '4', '5']:
            if k in classes_dict:
                for f in ['mvt_debit', 'mvt_credit', 'solde_debit', 'solde_credit']:
                    bilan[f] += classes_dict[k][f]

        # Totaux comptes de gestion (classes 6-8)
        gestion = self._empty_totals()
        gestion['label'] = _('Totaux comptes de gestion')
        for k in ['6', '7', '8']:
            if k in classes_dict:
                for f in ['mvt_debit', 'mvt_credit', 'solde_debit', 'solde_credit']:
                    gestion[f] += classes_dict[k][f]

        # Grand total
        grand_total = {
            'label': _('Totaux de la balance'),
            'mvt_debit': bilan['mvt_debit'] + gestion['mvt_debit'],
            'mvt_credit': bilan['mvt_credit'] + gestion['mvt_credit'],
            'solde_debit': bilan['solde_debit'] + gestion['solde_debit'],
            'solde_credit': bilan['solde_credit'] + gestion['solde_credit'],
        }

        res.update({
            'Classes': classes_list,
            'Bilan': bilan,
            'Gestion': gestion,
            'GrandTotal': grand_total,
        })
        return res
