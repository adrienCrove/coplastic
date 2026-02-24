# -*- coding: utf-8 -*-
from odoo import models, fields, _


class SaleStockCheckWizard(models.TransientModel):
    _name = 'sale.stock.check.wizard'
    _description = "Vérification des stocks avant confirmation de commande"

    order_id = fields.Many2one('sale.order', string="Commande", required=True, ondelete='cascade')
    line_ids = fields.One2many('sale.stock.check.wizard.line', 'wizard_id', string="Produits")

    def action_validate(self):
        """Ajuster les quantités au stock disponible, puis confirmer la commande."""
        for wiz_line in self.line_ids:
            wiz_line.order_line_id.product_uom_qty = wiz_line.available_qty
        self.order_id.action_confirm()
        return {'type': 'ir.actions.act_window_close'}


class SaleStockCheckWizardLine(models.TransientModel):
    _name = 'sale.stock.check.wizard.line'
    _description = "Ligne de vérification de stock"

    wizard_id = fields.Many2one('sale.stock.check.wizard', required=True, ondelete='cascade')
    order_line_id = fields.Many2one('sale.order.line', string="Ligne de commande", required=True)
    product_id = fields.Many2one(
        'product.product', related='order_line_id.product_id', readonly=True, string="Produit")
    requested_qty = fields.Float(string="Qté demandée", readonly=True)
    available_qty = fields.Float(string="Qté disponible", readonly=True)
    uom_id = fields.Many2one(
        'uom.uom', related='order_line_id.product_uom', readonly=True, string="Unité")
