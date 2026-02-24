# -*- coding: utf-8 -*-
import logging
from odoo import api, models, fields, _, Command

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    auto_reconcile_move_id = fields.Many2one(
        'account.move',
        string="Écriture de rapprochement automatique",
        readonly=True,
        copy=False,
    )
    show_manual_reconcile_button = fields.Boolean(
        compute='_compute_show_manual_reconcile_button',
    )

    @api.depends('state', 'auto_reconcile_move_id', 'journal_id.type')
    def _compute_show_manual_reconcile_button(self):
        for payment in self:
            payment.show_manual_reconcile_button = (
                payment.state == 'posted'
                and not payment.auto_reconcile_move_id
                and payment.journal_id.type in ('bank', 'cash')
            )

    def action_manual_reconcile(self):
        """Bouton de rapprochement manuel : crée l'écriture de contrepartie et lettre."""
        self.ensure_one()
        self._create_reconcile_entry()

    def action_open_reconcile_move(self):
        """Smart button : ouvre l'écriture de rapprochement."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Écriture de rapprochement"),
            'res_model': 'account.move',
            'res_id': self.auto_reconcile_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_post(self):
        res = super().action_post()
        self._create_auto_reconcile_entries()
        return res

    def _create_auto_reconcile_entries(self):
        """Crée les écritures de rapprochement pour les paiements sur des journaux auto-reconcile."""
        for payment in self:
            if payment.journal_id.auto_reconcile:
                payment._create_reconcile_entry()

    def _create_reconcile_entry(self):
        """Crée l'écriture de rapprochement pour un paiement.

        1. Crée une écriture qui inverse la ligne du compte de suspens
           et mouvemente le compte réel (default_account_id du journal).
        2. Valide cette écriture.
        3. Lettre les lignes du compte de suspens entre les deux écritures.
        """
        self.ensure_one()
        if not self.move_id or self.move_id.state != 'posted':
            return
        if self.auto_reconcile_move_id:
            return

        journal = self.journal_id
        outstanding_account = self.outstanding_account_id
        default_account = journal.default_account_id

        if not outstanding_account:
            _logger.warning(
                "Rapprochement: le paiement %s n'a pas de compte de suspens, ignoré.",
                self.display_name,
            )
            return

        if not default_account:
            _logger.warning(
                "Rapprochement: le journal %s n'a pas de compte par défaut, ignoré.",
                journal.display_name,
            )
            return

        if outstanding_account == default_account:
            return

        # Ligne de liquidité = la ligne sur le compte de suspens dans l'écriture du paiement
        liquidity_lines = self.move_id.line_ids.filtered(
            lambda l: l.account_id == outstanding_account
        )
        if not liquidity_lines:
            _logger.warning(
                "Rapprochement: pas de ligne de liquidité sur le compte %s "
                "pour le paiement %s, ignoré.",
                outstanding_account.code, self.display_name,
            )
            return

        liq_debit = sum(liquidity_lines.mapped('debit'))
        liq_credit = sum(liquidity_lines.mapped('credit'))
        liq_amount_currency = sum(liquidity_lines.mapped('amount_currency'))

        # Écriture de rapprochement :
        # - Ligne 1 : compte de suspens avec montants INVERSÉS (pour solder)
        # - Ligne 2 : compte réel du journal avec les montants originaux
        reconcile_move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': self.date,
            'ref': _("Rapprochement: %s", self.display_name),
            'move_type': 'entry',
            'line_ids': [
                Command.create({
                    'account_id': outstanding_account.id,
                    'name': _("Rapprochement %s", self.display_name),
                    'debit': liq_credit,
                    'credit': liq_debit,
                    'amount_currency': -liq_amount_currency,
                    'currency_id': self.currency_id.id,
                    'partner_id': self.partner_id.id,
                }),
                Command.create({
                    'account_id': default_account.id,
                    'name': _("Rapprochement %s", self.display_name),
                    'debit': liq_debit,
                    'credit': liq_credit,
                    'amount_currency': liq_amount_currency,
                    'currency_id': self.currency_id.id,
                    'partner_id': self.partner_id.id,
                }),
            ],
        })
        reconcile_move._post(soft=False)
        self.auto_reconcile_move_id = reconcile_move.id

        # Lettrage des lignes du compte de suspens
        if outstanding_account.reconcile:
            lines_to_reconcile = (
                self.move_id.line_ids + reconcile_move.line_ids
            ).filtered(
                lambda l: l.account_id == outstanding_account and not l.reconciled
            )
            if lines_to_reconcile:
                lines_to_reconcile.reconcile()
        else:
            _logger.warning(
                "Rapprochement: le compte %s (%s) n'autorise pas le lettrage. "
                "L'écriture a été créée mais les lignes ne sont pas lettrées.",
                outstanding_account.code, outstanding_account.name,
            )
