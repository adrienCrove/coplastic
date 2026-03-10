from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DepotVenteOrder(models.Model):
    _name = 'depot.vente.order'
    _description = 'Fiche de dépôt-vente'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_remise desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Référence',
        default='Nouveau',
        readonly=True,
        copy=False,
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendeur indépendant',
        required=True,
        tracking=True,
    )
    date_remise = fields.Date(
        string='Date de remise',
        default=fields.Date.today,
        required=True,
        tracking=True,
    )
    date_retour_prevue = fields.Date(
        string='Date de retour prévue',
    )
    location_src_id = fields.Many2one(
        'stock.location',
        string='Stock source',
        domain=[('usage', '=', 'internal')],
        help="Emplacement depuis lequel les produits sont remis au vendeur.",
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Emplacement vendeur',
        readonly=True,
        copy=False,
    )
    picking_out_id = fields.Many2one(
        'stock.picking',
        string='Bon de sortie',
        readonly=True,
        copy=False,
    )
    picking_in_id = fields.Many2one(
        'stock.picking',
        string='Bon de retour',
        readonly=True,
        copy=False,
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        readonly=True,
        copy=False,
    )
    line_ids = fields.One2many(
        'depot.vente.order.line',
        'order_id',
        string='Produits',
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'En cours'),
        ('returned', 'Retourné'),
        ('invoiced', 'Facturé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], default='draft', string='État', tracking=True, copy=False)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )
    amount_total = fields.Monetary(
        string='Total vendu',
        compute='_compute_amount_total',
        store=True,
        currency_field='currency_id',
    )
    note = fields.Text(string='Notes internes')

    # --- Computed counts for smart buttons ---

    picking_out_count = fields.Integer(compute='_compute_picking_counts')
    picking_in_count = fields.Integer(compute='_compute_picking_counts')
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    def _compute_picking_counts(self):
        for order in self:
            order.picking_out_count = 1 if order.picking_out_id else 0
            order.picking_in_count = 1 if order.picking_in_id else 0

    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = 1 if order.invoice_id else 0

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.line_ids.mapped('subtotal'))

    # --- Workflow actions ---

    def action_validate_remise(self):
        """Remet les produits au vendeur : crée et valide le transfert sortant."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Ajoutez au moins un produit avant de valider."))

        # Créer ou récupérer l'emplacement dédié au vendeur
        parent_location = self.env.ref('coplastic_depot_vente.location_depot_vente')
        location_dest = self.env['stock.location'].search([
            ('location_id', '=', parent_location.id),
            ('name', '=', self.partner_id.name),
        ], limit=1)
        if not location_dest:
            location_dest = self.env['stock.location'].create({
                'name': self.partner_id.name,
                'location_id': parent_location.id,
                'usage': 'internal',
            })

        # Emplacement source par défaut = stock principal du dépôt
        if not self.location_src_id:
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', self.company_id.id)], limit=1
            )
            self.location_src_id = warehouse.lot_stock_id

        # Type de transfert interne
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)
        if not picking_type:
            raise UserError(_("Aucun type de transfert interne trouvé pour votre société."))

        # Création du bon de sortie
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': location_dest.id,
            'origin': self.name,
            'partner_id': self.partner_id.id,
            'move_ids': [(0, 0, {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty_given,
                'product_uom': line.uom_id.id or line.product_id.uom_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': location_dest.id,
            }) for line in self.line_ids],
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.with_context(skip_immediate=True, skip_backorder=True).button_validate()

        # Numérotation séquentielle
        self.name = self.env['ir.sequence'].next_by_code('depot.vente.order') or self.name
        self.write({
            'state': 'active',
            'location_dest_id': location_dest.id,
            'picking_out_id': picking.id,
        })
        self.message_post(body=_("Produits remis au vendeur %s.", self.partner_id.name))

    def action_validate_retour(self):
        """Enregistre le retour des invendus et crée le transfert entrant."""
        self.ensure_one()
        lines_with_return = self.line_ids.filtered(lambda l: l.qty_returned > 0)

        if lines_with_return:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('warehouse_id.company_id', '=', self.company_id.id),
            ], limit=1)

            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': self.location_dest_id.id,
                'location_dest_id': self.location_src_id.id,
                'origin': self.name + ' - Retour',
                'partner_id': self.partner_id.id,
                'move_ids': [(0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty_returned,
                    'product_uom': line.uom_id.id or line.product_id.uom_id.id,
                    'location_id': self.location_dest_id.id,
                    'location_dest_id': self.location_src_id.id,
                }) for line in lines_with_return],
            })
            picking.action_confirm()
            picking.action_assign()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            picking.with_context(skip_immediate=True, skip_backorder=True).button_validate()
            self.picking_in_id = picking.id

        self.state = 'returned'
        self.message_post(body=_("Retour enregistré. Quantités vendues calculées."))

    def action_create_invoice(self):
        """Génère la facture client pour les produits effectivement vendus."""
        self.ensure_one()
        lines_sold = self.line_ids.filtered(lambda l: l.qty_sold > 0)
        if not lines_sold:
            raise UserError(_("Aucun produit vendu à facturer."))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.qty_sold,
                'price_unit': line.price_unit,
            }) for line in lines_sold],
        })
        self.write({'invoice_id': invoice.id, 'state': 'invoiced'})
        self.message_post(body=_("Facture %s générée.", invoice.name))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def action_reset_draft(self):
        self.write({'state': 'draft', 'name': 'Nouveau'})

    # --- Smart button actions ---

    def action_view_picking_out(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_out_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_picking_in(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_in_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
