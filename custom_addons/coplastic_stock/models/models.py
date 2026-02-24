# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CoplasticProduct(models.Model):
    _inherit = 'product.template'

    stock_alert_qty = fields.Float(
        string="Seuil d'alerte stock",
        default=1.0,
        help="Envoyer une alerte par email quand le stock disponible descend sous ce seuil. "
             "Laisser à 1 pour désactiver l'alerte.",
    )


class CoplasticStockAlert(models.AbstractModel):
    _name = 'coplastic.stock.alert'
    _description = "Alertes de stock Coplastic"

    @api.model
    def _check_stock_levels(self):
        """Cron quotidien : vérifie les stocks et envoie un email si des produits sont en pénurie."""
        # Trouver les produits avec un seuil configuré
        products = self.env['product.template'].search([
            ('stock_alert_qty', '>', 0),
            ('type', '=', 'product'),
            ('sale_ok', '=', True),
        ])

        low_stock = []
        for product in products:
            qty = product.qty_available
            if qty < product.stock_alert_qty:
                low_stock.append({
                    'name': product.name,
                    'qty': qty,
                    'uom': product.uom_id.name,
                    'threshold': product.stock_alert_qty,
                })

        if not low_stock:
            return

        # Construire le corps de l'email
        rows = ''.join(
            '<tr>'
            '<td style="padding:8px;border:1px solid #ddd;">%s</td>'
            '<td style="padding:8px;border:1px solid #ddd;text-align:right;color:%s;font-weight:bold;">%.2f %s</td>'
            '<td style="padding:8px;border:1px solid #ddd;text-align:right;">%.2f %s</td>'
            '</tr>' % (
                p['name'],
                'red' if p['qty'] <= 0 else 'orange',
                p['qty'], p['uom'],
                p['threshold'], p['uom'],
            )
            for p in low_stock
        )

        body = """
        <p>Bonjour,</p>
        <p>Les produits suivants ont atteint ou dépassé leur seuil d'alerte de stock :</p>
        <table style="border-collapse:collapse;width:100%%;">
            <thead>
                <tr style="background:#f0f0f0;">
                    <th style="padding:8px;border:1px solid #ddd;text-align:left;">Produit</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:right;">Stock actuel</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:right;">Seuil d'alerte</th>
                </tr>
            </thead>
            <tbody>%s</tbody>
        </table>
        <p>Merci de procéder au réapprovisionnement nécessaire.</p>
        <p><em>Coplastic - Gestion des stocks</em></p>
        """ % rows

        # Destinataires : tous les responsables stock + administrateurs
        group_stock = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        group_admin = self.env.ref('base.group_system', raise_if_not_found=False)
        recipients = self.env['res.users']
        if group_stock:
            recipients |= group_stock.users
        if group_admin:
            recipients |= group_admin.users

        emails = ','.join(filter(None, recipients.mapped('email')))
        if not emails:
            return

        company = self.env.company
        self.env['mail.mail'].create({
            'subject': '[%s] Alerte stock - %d produit(s) en pénurie' % (company.name, len(low_stock)),
            'email_from': company.email or '',
            'email_to': emails,
            'body_html': body,
            'auto_delete': True,
        }).send()

        # Notification dans le canal Discuss
        summary = '<b>Rapport quotidien — %d produit(s) en pénurie :</b><ul>%s</ul>' % (
            len(low_stock),
            ''.join('<li>%s : <b style="color:%s">%.2f %s</b> (seuil : %.2f)</li>' % (
                p['name'],
                'red' if p['qty'] <= 0 else 'orange',
                p['qty'], p['uom'], p['threshold']
            ) for p in low_stock)
        )
        Channel = self.env['discuss.channel'].sudo()
        channel = Channel.search([('name', '=', 'Alertes Stock')], limit=1)
        if not channel:
            channel = Channel.create({
                'name': 'Alertes Stock',
                'channel_type': 'channel',
                'description': 'Notifications automatiques de rupture de stock',
            })
            for partner in recipients.mapped('partner_id'):
                channel.add_members(partner_ids=partner.ids)
        channel.sudo().message_post(
            body=summary,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=self.env.company.partner_id.id,
        )


class CoplasticStockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """Après validation d'un mouvement de stock, vérifier les seuils d'alerte."""
        res = super()._action_done(cancel_backorder=cancel_backorder)

        # Récupérer les produits affectés par ces mouvements (sorties uniquement)
        products_to_check = self.filtered(
            lambda m: m.location_dest_id.usage != 'internal' or
                      m.location_id.usage == 'internal'
        ).product_id.product_tmpl_id.filtered(
            lambda t: t.stock_alert_qty > 0 and t.type == 'product' and t.sale_ok
        )

        if not products_to_check:
            return res

        # Destinataires : responsables stock + admins
        group_stock = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        group_admin = self.env.ref('base.group_system', raise_if_not_found=False)
        recipients = self.env['res.users']
        if group_stock:
            recipients |= group_stock.users
        if group_admin:
            recipients |= group_admin.users

        partners = recipients.mapped('partner_id')

        for product in products_to_check:
            qty = product.qty_available
            if qty < product.stock_alert_qty:
                color = 'danger' if qty <= 0 else 'warning'
                title = 'Rupture de stock !' if qty <= 0 else 'Stock faible !'
                message = '%s : %s %s restant(s) (seuil : %s %s)' % (
                    product.name,
                    qty, product.uom_id.name,
                    product.stock_alert_qty, product.uom_id.name,
                )
                # Notification temps réel (popup)
                for partner in partners:
                    self.env['bus.bus']._sendone(
                        partner,
                        'simple_notification',
                        {
                            'title': title,
                            'message': message,
                            'type': color,
                            'sticky': True,
                        }
                    )
                # Notification dans le canal de discussion
                self._post_stock_alert_to_channel(title, message, recipients)
        return res

    def _post_stock_alert_to_channel(self, title, message, recipients):
        """Poste une alerte dans le canal 'Alertes Stock' de Discuss."""
        Channel = self.env['discuss.channel'].sudo()
        channel = Channel.search([('name', '=', 'Alertes Stock')], limit=1)
        if not channel:
            channel = Channel.create({
                'name': 'Alertes Stock',
                'channel_type': 'channel',
                'description': 'Notifications automatiques de rupture de stock',
            })
            # Ajouter les managers comme membres
            for partner in recipients.mapped('partner_id'):
                channel.add_members(partner_ids=partner.ids)
        channel.sudo().message_post(
            body='<b>%s</b><br/>%s' % (title, message),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=self.env.company.partner_id.id,
        )


class StockPickingPrintHistory(models.Model):
    _name = 'stock.picking.print.history'
    _description = "Historique d'impression - Bon de livraison"
    _order = 'print_date DESC'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Bon de livraison',
        ondelete='cascade',
        required=True,
        index=True,
    )
    print_date = fields.Datetime(
        string="Date/Heure",
        readonly=True,
        required=True,
        default=fields.Datetime.now,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Utilisateur',
        readonly=True,
        required=True,
        default=lambda self: self.env.user,
    )
    print_number = fields.Integer(
        string="N° impression",
        readonly=True,
    )


class CoplasticStockPicking(models.Model):
    _inherit = 'stock.picking'

    last_print_date = fields.Datetime(
        string="Dernière impression",
        readonly=True,
        copy=False,
    )
    print_history_ids = fields.One2many(
        'stock.picking.print.history',
        'picking_id',
        string="Historique d'impressions",
        readonly=True,
    )
    def do_print_picking(self):
        """État 'assigned' : le bouton appelle cette méthode."""
        self._create_print_history()
        return super().do_print_picking()

    def action_print_delivery_slip(self):
        """État 'done' : remplace l'appel direct au rapport."""
        self._create_print_history()
        return self.env.ref('stock.action_report_delivery').report_action(self)

    def _create_print_history(self):
        """Crée un enregistrement d'historique d'impression."""
        for picking in self:
            count = len(picking.print_history_ids) + 1
            self.env['stock.picking.print.history'].create({
                'picking_id': picking.id,
                'print_number': count,
            })
            picking.last_print_date = fields.Datetime.now()
