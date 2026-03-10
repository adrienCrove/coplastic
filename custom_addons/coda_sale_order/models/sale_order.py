from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    numero_da = fields.Char(
        string='N° DA',
        copy=False,
        help="Numéro de Demande d'Achat lié à ce devis/bon de commande.",
    )
    coefficient_selectivite = fields.Float(
        string='Coefficient de sélectivité',
        digits=(16, 4),
        default=0.0,
        help="Coefficient appliqué à toutes les lignes : Prix de vente = Prix de revient × Coefficient",
    )
    marge_totale = fields.Monetary(
        string='Marge totale',
        compute='_compute_marge_totale',
        store=True,
        currency_field='currency_id',
        help="Somme des marges unitaires × quantités de toutes les lignes produit",
    )

    @api.depends('order_line.prix_de_marge', 'order_line.product_uom_qty', 'order_line.display_type')
    def _compute_marge_totale(self):
        for order in self:
            order.marge_totale = sum(
                line.prix_de_marge * line.product_uom_qty
                for line in order.order_line
                if not line.display_type
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New') or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('coda.sale.quotation') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order.name = self.env['ir.sequence'].next_by_code('coda.sale.order') or order.name
        return res

    def action_delete_order_lines(self):
        """Supprime toutes les lignes produit du devis (hors sections/notes)."""
        for order in self:
            if order.state not in ('draft', 'sent'):
                raise UserError(_("Impossible de supprimer les lignes d'une commande confirmée."))
            order.order_line.unlink()

    @api.onchange('coefficient_selectivite')
    def _onchange_coefficient_selectivite(self):
        """Recalcule le prix de vente de toutes les lignes produit."""
        coeff = self.coefficient_selectivite
        if not coeff:
            return
        for line in self.order_line:
            if not line.display_type and line.prix_de_revient:
                line.price_unit = line.prix_de_revient * coeff
