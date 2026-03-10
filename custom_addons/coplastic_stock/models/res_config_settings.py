# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_alert_qty_default = fields.Float(
        string="Seuil d'alerte stock global",
        config_parameter='coplastic_stock.stock_alert_qty_default',
        default=0.0,
        help="Seuil par défaut appliqué à tous les produits dont le seuil individuel n'a pas été modifié. "
             "Mettre à 0 pour désactiver l'alerte globale.",
    )

    def set_values(self):
        super().set_values()
        new_default = self.stock_alert_qty_default
        # Mettre à jour les produits qui ont encore la valeur de l'ancien paramètre
        old_param = float(self.env['ir.config_parameter'].sudo().get_param(
            'coplastic_stock.stock_alert_qty_default', 0.0
        ) or 0.0)
        if old_param != new_default and new_default > 0:
            # Met à jour uniquement les produits ayant encore l'ancienne valeur par défaut
            products = self.env['product.template'].search([
                ('stock_alert_qty', '=', old_param),
                ('type', '=', 'product'),
            ])
            if products:
                products.write({'stock_alert_qty': new_default})
