# -*- coding: utf-8 -*-
from odoo import api, models

OHADA_CLASSES = {
    '1': 'CLASSE 1 - COMPTES DE RESSOURCES DURABLES',
    '2': 'CLASSE 2 - ACTIF IMMOBILISÉ',
    '3': 'CLASSE 3 - COMPTES DE STOCKS',
    '4': 'CLASSE 4 - TIERS',
    '5': 'CLASSE 5 - TRÉSORERIE',
    '6': 'CLASSE 6 - CHARGES',
    '7': 'CLASSE 7 - PRODUITS',
    '8': 'CLASSE 8 - AUTRES CHARGES ET PRODUITS',
}


class ReportPartnerLedger(models.AbstractModel):
    _inherit = 'report.base_accounting_kit.report_partnerledger'

    _REFUND_MOVE_TYPES = {'out_refund', 'in_refund'}

    def _grand_total_partner_ledger(self, data, partner_ids=None):
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        reconcile_clause = '' if data['form']['reconciled'] \
            else ' AND "account_move_line".full_reconcile_id IS NULL '
        params = [tuple(self._REFUND_MOVE_TYPES)]
        where_parts = []
        if partner_ids:
            where_parts.append('"account_move_line".partner_id IN %s')
            params.append(tuple(partner_ids))
        where_parts += [
            'm.id = "account_move_line".move_id',
            'm.state IN %s',
            '"account_move_line".account_id IN %s',
            query_get_data[1] + reconcile_clause,
        ]
        params += [tuple(data['computed']['move_state']),
                   tuple(data['computed']['account_ids'])] + query_get_data[2]
        query = (
            'SELECT '
            'COALESCE(SUM("account_move_line".debit), 0.0), '
            'COALESCE(SUM("account_move_line".credit), 0.0), '
            'COALESCE(SUM("account_move_line".debit - "account_move_line".credit), 0.0), '
            'COALESCE(SUM(CASE WHEN m.move_type IN %s '
            'THEN "account_move_line".credit ELSE 0.0 END), 0.0) '
            'FROM ' + query_get_data[0] + ', account_move AS m '
            'WHERE ' + ' AND '.join(where_parts)
        )
        self.env.cr.execute(query, tuple(params))
        debit, credit, balance, facture_avoir = self.env.cr.fetchone() or (0.0, 0.0, 0.0, 0.0)
        return {
            'debit': debit or 0.0,
            'credit': credit or 0.0,
            'balance': balance or 0.0,
            'facture_avoir': facture_avoir or 0.0,
        }


    def _lines_for_account(self, data, partner, account_id):
        """Lignes de mouvement pour un partenaire sur un compte spécifique."""
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        reconcile_clause = '' if data['form']['reconciled'] \
            else ' AND "account_move_line".full_reconcile_id IS NULL '
        params = [partner.id, tuple(data['computed']['move_state']),
                  account_id] + query_get_data[2]
        query = """
            SELECT "account_move_line".id, "account_move_line".date, j.code,
             acc.code as a_code, acc.name as a_name, "account_move_line".ref,
             m.name as move_name, m.move_type, "account_move_line".name,
             "account_move_line".debit, "account_move_line".credit,
             "account_move_line".amount_currency,
             "account_move_line".currency_id, c.symbol AS currency_code
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id = %s AND """ + \
                query_get_data[1] + reconcile_clause + """
                ORDER BY "account_move_line".date"""
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.dictfetchall()
        running = 0.0
        currency = self.env['res.currency']
        for r in rows:
            r['displayed_name'] = '-'.join(
                r[f] for f in ('move_name', 'ref', 'name')
                if r[f] not in (None, '', '/')
            )
            r['facture_avoir'] = r['credit'] if r.get('move_type') in self._REFUND_MOVE_TYPES else 0.0
            running += r['debit'] - r['credit']
            r['progress'] = running
            r['currency_id'] = currency.browse(r.get('currency_id'))
        return rows

    def _sum_partner_account(self, data, partner, account_id, field):
        """Totaux debit/credit pour un partenaire sur un compte spécifique."""
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        reconcile_clause = '' if data['form']['reconciled'] \
            else ' AND "account_move_line".full_reconcile_id IS NULL '
        if field == 'facture_avoir':
            params = [tuple(self._REFUND_MOVE_TYPES), partner.id,
                      tuple(data['computed']['move_state']), account_id] + query_get_data[2]
            query = """SELECT COALESCE(SUM(CASE WHEN m.move_type IN %s THEN account_move_line.credit ELSE 0.0 END), 0.0)
                    FROM """ + query_get_data[0] + """, account_move AS m
                    WHERE "account_move_line".partner_id = %s
                        AND m.id = "account_move_line".move_id
                        AND m.state IN %s
                        AND account_id = %s
                        AND """ + query_get_data[1] + reconcile_clause
            self.env.cr.execute(query, tuple(params))
            row = self.env.cr.fetchone()
            return (row[0] or 0.0) if row else 0.0
        if field not in ['debit', 'credit', 'debit - credit']:
            return 0.0
        params = [partner.id, tuple(data['computed']['move_state']),
                  account_id] + query_get_data[2]
        query = """SELECT sum(""" + field + """)
                FROM """ + query_get_data[0] + """, account_move AS m
                WHERE "account_move_line".partner_id = %s
                    AND m.id = "account_move_line".move_id
                    AND m.state IN %s
                    AND account_id = %s
                    AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        row = self.env.cr.fetchone()
        return (row[0] or 0.0) if row else 0.0

    def _build_docs_by_class(self, data, docs):
        """
        Retourne [(class_label, [(acc_id, acc_code, acc_name, [partners])])]
        trie par code de compte.
        """
        if not docs:
            return []
        account_ids = data['computed']['account_ids']
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        reconcile_clause = '' if data['form']['reconciled'] \
            else ' AND "account_move_line".full_reconcile_id IS NULL '
        partner_ids = [p.id for p in docs]
        params = [tuple(partner_ids), tuple(data['computed']['move_state']),
                  tuple(account_ids)] + query_get_data[2]
        query = """
            SELECT DISTINCT "account_move_line".partner_id,
                            acc.id, acc.code, acc.name
            FROM """ + query_get_data[0] + """
            JOIN account_account acc ON acc.id = "account_move_line".account_id
            JOIN account_move am ON am.id = "account_move_line".move_id
            WHERE "account_move_line".partner_id IN %s
              AND am.state IN %s
              AND "account_move_line".account_id IN %s
              AND """ + query_get_data[1] + reconcile_clause + """
            ORDER BY acc.code
        """
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.fetchall()

        partner_map = {p.id: p for p in docs}
        acc_data = {}
        for partner_id, acc_id, acc_code, acc_name in rows:
            if acc_id not in acc_data:
                name_str = acc_name.get('fr_FR') or acc_name.get('en_US', '') \
                    if isinstance(acc_name, dict) else (acc_name or '')
                acc_data[acc_id] = {
                    'code': acc_code,
                    'name': name_str,
                    'partners': [],
                    '_seen': set(),
                }
            if partner_id not in acc_data[acc_id]['_seen']:
                acc_data[acc_id]['partners'].append(partner_map[partner_id])
                acc_data[acc_id]['_seen'].add(partner_id)

        classes = {}
        for acc_id, info in sorted(acc_data.items(), key=lambda x: x[1]['code']):
            digit = info['code'][0] if info['code'] else '4'
            label = OHADA_CLASSES.get(digit, f'CLASSE {digit}')
            if label not in classes:
                classes[label] = []
            partners_sorted = sorted(info['partners'],
                                     key=lambda p: (p.ref or '', p.name or ''))
            classes[label].append((acc_id, info['code'], info['name'],
                                   partners_sorted))

        return list(classes.items())

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data=data)
        form = data.get('form', {}) if data else {}

        supplier_ids = form.get('supplier_ids')
        customer_ids = form.get('customer_ids')
        if supplier_ids:
            res['docs'] = [p for p in res['docs'] if p.id in supplier_ids]
            res['doc_ids'] = supplier_ids
        elif customer_ids:
            res['docs'] = [p for p in res['docs'] if p.id in customer_ids]
            res['doc_ids'] = customer_ids

        account_ids_filter = form.get('account_ids_filter', [])
        if account_ids_filter:
            filtered = [aid for aid in data['computed']['account_ids']
                        if aid in account_ids_filter]
            if filtered:
                data['computed']['account_ids'] = filtered
                self.env.cr.execute("""
                    SELECT DISTINCT aml.partner_id
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    WHERE aml.partner_id IS NOT NULL
                      AND aml.account_id IN %s
                      AND am.state IN %s
                """, (tuple(filtered), tuple(data['computed']['move_state'])))
                partner_ids_on_accounts = {r[0] for r in self.env.cr.fetchall()}
                res['docs'] = [p for p in res['docs']
                               if p.id in partner_ids_on_accounts]
                res['doc_ids'] = [p.id for p in res['docs']]

        res['docs_by_class'] = self._build_docs_by_class(data, res['docs'])
        res['lines_for_account'] = self._lines_for_account
        res['sum_partner_account'] = self._sum_partner_account
        res['grand_totals'] = self._grand_total_partner_ledger(
            data, [partner.id for partner in res['docs']]
        )

        currency_symbol = self.env.company.currency_id.symbol or 'CFA'

        def fmt(amount):
            if amount is None:
                amount = 0.0
            sign = '-' if amount < 0 else ''
            formatted = '{:,.0f}'.format(abs(amount)).replace(',', ' ')
            return f"{sign}{formatted} {currency_symbol}"

        res['fmt'] = fmt
        return res
