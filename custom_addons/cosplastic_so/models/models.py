# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CoplasticPartner(models.Model):
    _inherit = 'res.partner'

    rccm = fields.Char(string="N°RCCM", help="Numéro du Registre du Commerce et du Crédit Mobilier")
    ncc = fields.Char(string="NCC", help="Numéro de Compte Contribuable (NCC)")


class CoplasticSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('validity_date')
    def _check_validity_date(self):
        for order in self:
            if not order.validity_date or not order.date_order:
                continue
            order_date = order.date_order.date()
            max_date = order_date + timedelta(days=14)
            if order.validity_date < order_date:
                raise ValidationError(_(
                    "La date d'expiration ne peut pas être antérieure à la date du devis (%s).",
                    order_date.strftime('%d/%m/%Y')
                ))
            if order.validity_date > max_date:
                raise ValidationError(_(
                    "La date d'expiration ne peut pas dépasser 14 jours après la date du devis. "
                    "Date maximum autorisée : %s",
                    max_date.strftime('%d/%m/%Y')
                ))

    def _should_be_locked(self):
        """Toujours verrouiller les commandes confirmées.
        L'admin peut déverrouiller manuellement via le bouton Déverrouiller."""
        self.ensure_one()
        return True

    def action_unlock(self):
        """Seul l'administrateur peut déverrouiller une commande."""
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_(
                "Seul l'administrateur peut déverrouiller un bon de commande."
            ))
        return super().action_unlock()

    def unlink(self):
        """Seul l'administrateur peut supprimer des devis/bons de commande."""
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_(
                "Vous n'avez pas le droit de supprimer des devis ou bons de commande. "
                "Seul l'administrateur peut effectuer cette action."
            ))
        return super().unlink()

    def action_confirm(self):
        """Vérifier les stocks avant de confirmer : bloquer si rupture, sinon afficher un avertissement."""
        for order in self:
            storable_lines = order.order_line.filtered(
                lambda l: l.product_id and l.product_id.type == 'product'
            )

            zero_stock = []
            insufficient = []

            for line in storable_lines:
                available = line.product_id.qty_available
                if available <= 0:
                    zero_stock.append(line.product_id.display_name)
                elif line.product_uom_qty > available:
                    insufficient.append({
                        'line': line,
                        'available': available,
                    })

            if zero_stock:
                raise UserError(_(
                    "Opération impossible. Les produits suivants sont en rupture de stock :\n\n%s"
                ) % '\n'.join('• ' + p for p in zero_stock))

            if insufficient:
                wizard = self.env['sale.stock.check.wizard'].create({
                    'order_id': order.id,
                    'line_ids': [(0, 0, {
                        'order_line_id': item['line'].id,
                        'requested_qty': item['line'].product_uom_qty,
                        'available_qty': item['available'],
                    }) for item in insufficient],
                })
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Stock insuffisant'),
                    'res_model': 'sale.stock.check.wizard',
                    'res_id': wizard.id,
                    'view_mode': 'form',
                    'target': 'new',
                }

        return super().action_confirm()
