from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    coefficient_selectivite = fields.Float(
        string='Coefficient ligne',
        digits=(16, 4),
        default=0.0,
        help="Coefficient de sélectivité propre à cette ligne.",
    )
    prix_de_revient = fields.Float(
        string='Prix de revient',
        digits='Product Price',
        help="Coût d'achat ou de production. Initialisé depuis le prix de revient du produit.",
    )
    prix_de_marge = fields.Float(
        string='Marge',
        digits='Product Price',
        compute='_compute_prix_de_marge',
        store=True,
        help="Marge = Prix de vente - Prix de revient",
    )

    @api.depends('price_unit', 'prix_de_revient')
    def _compute_prix_de_marge(self):
        for line in self:
            line.prix_de_marge = (line.price_unit or 0.0) - (line.prix_de_revient or 0.0)

    @api.onchange('product_id')
    def _onchange_product_id_prix_revient(self):
        """Initialise le prix de revient depuis le coût du produit à la sélection."""
        if self.product_id:
            self.prix_de_revient = self.product_id.standard_price
