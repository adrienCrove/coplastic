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

    stock_alert_user_ids = fields.Many2many(
        'res.users',
        relation='coplastic_stock_alert_user_rel',
        column1='settings_id',
        column2='user_id',
        string="Destinataires des alertes stock",
        help="Utilisateurs qui recevront les emails et notifications d'alerte de stock. "
             "Si vide, les responsables stock et administrateurs sont notifiés par défaut.",
    )

    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'coplastic_stock.stock_alert_user_ids', ''
        )
        user_ids = [int(i) for i in param.split(',') if i.strip().isdigit()]
        res['stock_alert_user_ids'] = [(6, 0, user_ids)]
        return res

    def set_values(self):
        super().set_values()
        # Sauvegarder les utilisateurs sélectionnés
        user_ids = self.stock_alert_user_ids.ids
        self.env['ir.config_parameter'].sudo().set_param(
            'coplastic_stock.stock_alert_user_ids',
            ','.join(str(i) for i in user_ids),
        )
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
