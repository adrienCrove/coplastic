# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class SaleOrderCreditLimit(models.Model):
    _inherit = 'sale.order'

    def _get_total_credit_exposure(self):
        """Factures impayées + BCs confirmés non facturés + montant du BC en cours."""
        partner = self.partner_id.commercial_partner_id
        current_amount = self.currency_id._convert(
            self.amount_total,
            self.company_id.currency_id,
            self.company_id,
            self.date_order or fields.Date.today(),
        )
        return partner.credit + partner.credit_to_invoice + current_amount

    def _action_confirm(self):
        """Bloque si l'exposition totale dépasse le blocking_stage."""
        if self.partner_id.active_limit and self.partner_id.enable_credit_limit:
            if self.partner_id.blocking_stage != 0:
                total_exposure = self._get_total_credit_exposure()
                if total_exposure >= self.partner_id.blocking_stage:
                    raise UserError(_(
                        "%(name)s dépasse la limite de blocage.\n"
                        "Exposition totale : %(exposure)s %(symbol)s "
                        "(factures impayées + BCs confirmés non facturés + ce BC)\n"
                        "Limite de blocage : %(limit)s %(symbol)s",
                        name=self.partner_id.name,
                        exposure=round(total_exposure, 2),
                        symbol=self.currency_id.symbol,
                        limit=self.partner_id.blocking_stage,
                    ))
        return super()._action_confirm()

    @api.onchange('partner_id', 'order_line', 'amount_total')
    def check_due(self):
        """Alerte visuelle tenant compte du montant du BC en cours."""
        self.has_due = False
        self.is_warning = False
        if not (self.partner_id and self.partner_id.active_limit
                and self.partner_id.enable_credit_limit):
            return
        total_exposure = self._get_total_credit_exposure()
        if total_exposure > 0:
            self.has_due = True
        if self.partner_id.warning_stage != 0 and total_exposure >= self.partner_id.warning_stage:
            self.is_warning = True


class AccountMoveCreditLimit(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Bloque la validation de facture si l'exposition totale dépasse le blocking_stage."""
        pay_type = ['out_invoice', 'out_refund', 'out_receipt']
        for rec in self:
            if not (rec.partner_id.active_limit and rec.move_type in pay_type
                    and rec.partner_id.enable_credit_limit):
                continue
            if rec.partner_id.blocking_stage == 0:
                continue
            partner = rec.partner_id.commercial_partner_id
            current_amount = rec.currency_id._convert(
                rec.amount_total,
                rec.company_id.currency_id,
                rec.company_id,
                rec.invoice_date or fields.Date.today(),
            )
            # Pour une facture issue d'un BC, le montant du BC est déjà dans
            # credit_to_invoice — on l'exclut pour éviter le double comptage.
            exclude = rec._get_partner_credit_warning_exclude_amount() if hasattr(rec, '_get_partner_credit_warning_exclude_amount') else 0.0
            total_exposure = partner.credit + partner.credit_to_invoice - exclude + current_amount
            if total_exposure >= rec.partner_id.blocking_stage:
                raise UserError(_(
                    "%(name)s dépasse la limite de blocage.\n"
                    "Exposition totale : %(exposure)s %(symbol)s\n"
                    "Limite de blocage : %(limit)s %(symbol)s",
                    name=rec.partner_id.name,
                    exposure=round(total_exposure, 2),
                    symbol=rec.currency_id.symbol,
                    limit=rec.partner_id.blocking_stage,
                ))
        return super().action_post()

    @api.onchange('partner_id', 'amount_total')
    def check_due(self):
        """Alerte visuelle tenant compte du montant de la facture en cours."""
        self.has_due = False
        self.is_warning = False
        if not (self.partner_id and self.partner_id.active_limit
                and self.partner_id.enable_credit_limit):
            return
        partner = self.partner_id.commercial_partner_id
        current_amount = self.currency_id._convert(
            self.amount_total,
            self.company_id.currency_id,
            self.company_id,
            self.invoice_date or fields.Date.today(),
        ) if self.currency_id and self.company_id else self.amount_total
        total_exposure = partner.credit + partner.credit_to_invoice + current_amount
        if total_exposure > 0:
            self.has_due = True
        if self.partner_id.warning_stage != 0 and total_exposure >= self.partner_id.warning_stage:
            self.is_warning = True
