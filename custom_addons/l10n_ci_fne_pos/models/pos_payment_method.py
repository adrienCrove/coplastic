# -*- coding: utf-8 -*-

from odoo import fields, models

from odoo.addons.l10n_ci_fne.models.fne_api import FNE_PAYMENT_METHODS


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    fne_payment_method = fields.Selection(
        FNE_PAYMENT_METHODS,
        string="Mode de paiement FNE",
        help="Valeur transmise à la DGI dans le champ paymentMethod lors de la "
             "certification d'un ticket réglé avec ce mode.\n"
             "Laissé vide, le module déduit « Espèces » pour un mode de type "
             "caisse et « Carte bancaire » sinon."
    )

    def _get_fne_payment_method(self):
        """Valeur FNE effective, avec repli sur le type du mode de paiement."""
        self.ensure_one()
        if self.fne_payment_method:
            return self.fne_payment_method
        return 'cash' if self.is_cash_count else 'card'
