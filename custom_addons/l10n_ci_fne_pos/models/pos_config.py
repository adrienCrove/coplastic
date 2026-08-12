# -*- coding: utf-8 -*-

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    fne_point_of_sale = fields.Char(
        string="Point de vente FNE",
        help="Identifiant de ce point de vente tel qu'il est déclaré auprès de "
             "la DGI. La plateforme refuse toute valeur qu'elle ne connaît pas "
             "(erreur « Point of sale is invalid »).\n"
             "Laissé vide, le point de vente global des paramètres FNE est utilisé."
    )

    def _get_fne_point_of_sale(self):
        """Valeur transmise dans le champ `pointOfSale`, avec repli sur le
        point de vente global configuré pour l'entreprise."""
        self.ensure_one()
        if self.fne_point_of_sale:
            return self.fne_point_of_sale
        return self.env['ir.config_parameter'].sudo().get_param(
            'l10n_ci_fne.point_of_sale', '1'
        )
