from odoo import api, fields, models


class DepotVenteOrderLine(models.Model):
    _name = 'depot.vente.order.line'
    _description = 'Ligne de dépôt-vente'

    order_id = fields.Many2one(
        'depot.vente.order',
        string='Fiche dépôt-vente',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])],
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unité',
    )
    qty_given = fields.Float(
        string='Qté remise',
        digits='Product Unit of Measure',
        default=1.0,
    )
    qty_returned = fields.Float(
        string='Qté retournée',
        digits='Product Unit of Measure',
        default=0.0,
    )
    qty_sold = fields.Float(
        string='Qté vendue',
        compute='_compute_qty_sold',
        store=True,
        digits='Product Unit of Measure',
    )
    price_unit = fields.Float(
        string='Prix unitaire',
        digits='Product Price',
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id',
        store=True,
    )
    subtotal = fields.Monetary(
        string='Sous-total',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('qty_given', 'qty_returned')
    def _compute_qty_sold(self):
        for line in self:
            line.qty_sold = max(0.0, line.qty_given - line.qty_returned)

    @api.depends('qty_sold', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty_sold * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price
