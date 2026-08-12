# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_alert_days = fields.Integer(
        string="Alerte avant échéance (jours)",
        config_parameter='coplastic_account.invoice_alert_days',
        default=5,
        help="Nombre de jours avant l'échéance pour envoyer l'alerte de facture client.",
    )

    sale_order_alert_days = fields.Integer(
        string="Alerte commandes avant échéance (jours)",
        config_parameter='coplastic_account.sale_order_alert_days',
        default=2,
        help="Nombre de jours avant l'échéance calculée (date commande + conditions de paiement) pour alerter sur les commandes clients.",
    )

    def set_values(self):
        super().set_values()
        days = self.invoice_alert_days or 5
        rule = self.env.ref(
            'coplastic_account.automation_customer_invoice_due_soon',
            raise_if_not_found=False,
        )
        if rule:
            rule.trg_date_range = -days
