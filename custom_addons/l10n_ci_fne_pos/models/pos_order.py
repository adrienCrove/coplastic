# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.l10n_ci_fne.models import fne_utils
from odoo.addons.l10n_ci_fne.models.account_move import FNE_VAT_RATES
from odoo.addons.l10n_ci_fne.models.fne_api import FNE_PAYMENT_METHODS

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # === Champs FNE ===
    # Mêmes noms que sur account.move : le template d'impression normalisé est
    # partagé entre les deux modèles.
    fne_reference = fields.Char(
        string="Référence FNE", readonly=True, copy=False,
        help="Numéro de reçu normalisé attribué par la DGI"
    )
    fne_token = fields.Char(
        string="Token FNE", readonly=True, copy=False,
        help="URL de vérification FNE encodée dans le QR Code"
    )
    fne_qr_code = fields.Binary(
        string="QR Code FNE", compute='_compute_fne_qr_code', store=True, copy=False
    )
    fne_certified = fields.Boolean(
        string="Certifié FNE", readonly=True, copy=False, default=False
    )
    fne_invoice_id = fields.Char(
        string="ID FNE", readonly=True, copy=False,
        help="Identifiant du reçu sur la plateforme FNE"
    )
    fne_ncc = fields.Char(string="NCC Entreprise", readonly=True, copy=False)
    fne_balance_sticker = fields.Integer(
        string="Solde Stickers FNE", readonly=True, copy=False
    )
    fne_certification_date = fields.Datetime(
        string="Date de certification", readonly=True, copy=False
    )
    fne_error_message = fields.Text(string="Erreur FNE", readonly=True, copy=False)
    fne_simulation = fields.Boolean(
        string="Certification simulation", readonly=True, copy=False, default=False
    )
    fne_payment_method = fields.Selection(
        FNE_PAYMENT_METHODS, string="Mode de paiement FNE", readonly=True, copy=False
    )

    @api.depends('fne_token')
    def _compute_fne_qr_code(self):
        for order in self:
            order.fne_qr_code = fne_utils.generate_qr_code(order.fne_token)

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def _fne_get_payment_method(self):
        """Mode de paiement FNE du ticket : celui du règlement le plus élevé.

        Un ticket peut être réglé en plusieurs fois (espèces + carte) ; la DGI
        n'accepte qu'une valeur, on retient donc le règlement dominant.
        """
        self.ensure_one()
        payments = self.payment_ids.filtered(lambda p: p.amount > 0)
        if not payments:
            return 'cash'
        main = max(payments, key=lambda p: p.amount)
        return main.payment_method_id._get_fne_payment_method()

    def _fne_get_receipt_number(self):
        """Numéro de reçu transmis à la DGI dans le champ `rne`.

        C'est le numéro imprimé sur le ticket (colonne « Numéro de reçu » de
        l'écran Commandes) ; c'est lui qu'une facture de régularisation devra
        reprendre pour se rattacher à ce reçu.
        """
        self.ensure_one()
        return self.pos_reference or self.name or ''

    def action_fne_certify(self):
        """Certifie le ticket de caisse auprès de la plateforme FNE."""
        self.ensure_one()
        if self.fne_certified:
            raise UserError(_("Ce ticket est déjà certifié FNE."))
        if self.state not in ('paid', 'done', 'invoiced'):
            raise UserError(_(
                "Seul un ticket payé peut être certifié FNE.\n"
                "Statut actuel : %s"
            ) % self.state)

        result = self.env['l10n_ci_fne.api'].certify_pos_order(self)
        if not result.get('success'):
            return False

        receipt_data = result.get('invoice_data', {})
        self.write({
            'fne_reference': result.get('reference', ''),
            'fne_token': result.get('token', ''),
            'fne_ncc': result.get('ncc', ''),
            'fne_balance_sticker': result.get('balance_sticker', 0),
            'fne_invoice_id': receipt_data.get('id', ''),
            'fne_certified': True,
            'fne_simulation': result.get('simulation', False),
            'fne_certification_date': fields.Datetime.now(),
            'fne_payment_method': self._fne_get_payment_method(),
            'fne_error_message': False,
        })
        return True

    def action_fne_reset_simulation(self):
        """Réinitialise une certification faite en mode simulation."""
        self.ensure_one()
        if not self.fne_simulation:
            raise UserError(_("Ce ticket n'a pas été certifié en mode simulation."))
        self.write({
            'fne_reference': False, 'fne_token': False, 'fne_ncc': False,
            'fne_balance_sticker': 0, 'fne_invoice_id': False,
            'fne_certified': False, 'fne_simulation': False,
            'fne_certification_date': False, 'fne_payment_method': False,
            'fne_error_message': False,
        })

    @api.model
    def fne_certify_from_ui(self, order_id):
        """Point d'entrée RPC du bouton POS.

        Certifie le ticket s'il ne l'est pas encore, puis renvoie les données
        FNE nécessaires à l'impression. Les erreurs sont stockées sur le ticket
        avant d'être remontées, pour rester consultables depuis le backend.
        """
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_("Ticket introuvable."))
        if not order.fne_certified:
            try:
                order.action_fne_certify()
            except UserError as e:
                order.sudo().write({'fne_error_message': str(e)})
                raise
        return order._fne_export_for_printing()

    def _fne_export_for_printing(self):
        """Données FNE poussées vers le POS pour l'impression du ticket."""
        self.ensure_one()
        qr_code = ''
        if self.fne_qr_code:
            qr_code = 'data:image/png;base64,%s' % self.fne_qr_code.decode()
        certification_date = ''
        if self.fne_certification_date:
            certification_date = fields.Datetime.context_timestamp(
                self, self.fne_certification_date
            ).strftime('%d/%m/%Y %H:%M:%S')
        return {
            'fne_certified': self.fne_certified,
            'fne_simulation': self.fne_simulation,
            'fne_reference': self.fne_reference or '',
            'fne_ncc': self.fne_ncc or '',
            'fne_qr_code': qr_code,
            'fne_certification_date': certification_date,
        }

    def _export_for_ui(self, order):
        """Expose les champs FNE au POS pour que la réimpression les retrouve."""
        res = super()._export_for_ui(order)
        res.update(order._fne_export_for_printing())
        return res

    def _prepare_invoice_vals(self):
        """Rattache la facture au reçu normalisé dont elle est issue.

        Sans ce rattachement, un ticket déjà certifié puis facturé depuis le
        POS serait normalisé une seconde fois auprès de la DGI.
        """
        vals = super()._prepare_invoice_vals()
        if self.fne_certified:
            vals.update({
                'fne_is_rne': True,
                'fne_rne_number': self._fne_get_receipt_number(),
            })
        return vals

    # ------------------------------------------------------------------
    # Impression au format normalisé DGI
    # ------------------------------------------------------------------

    def action_fne_print_receipt(self):
        """Imprime le reçu au format normalisé DGI (PDF A4)."""
        self.ensure_one()
        return self.env.ref(
            'l10n_ci_fne_pos.action_report_pos_receipt_fne'
        ).report_action(self)

    def _fne_format_amount(self, amount):
        self.ensure_one()
        return fne_utils.format_amount(amount, self.currency_id.decimal_places or 0)

    @api.model
    def _fne_format_rate(self, rate):
        return fne_utils.format_rate(rate)

    @api.model
    def _fne_format_quantity(self, quantity):
        return fne_utils.format_quantity(quantity)

    def _fne_tax_label(self, tax):
        """Libellé de la colonne « Taxes (%) » : code FNE pour les taux TVA
        reconnus, nom de la taxe Odoo sinon."""
        if tax.amount_type == 'percent' and tax.amount in FNE_VAT_RATES:
            code = self.env['l10n_ci_fne.api']._get_fne_tax_type(tax.amount)
        else:
            code = tax.name or 'TAXE'
        return '%s (%s)' % (code, fne_utils.format_rate(tax.amount))

    def _fne_get_report_data(self):
        """Données du modèle normalisé DGI pour un ticket de caisse.

        Retourne les mêmes clés que account.move._fne_get_report_data() : le
        corps du template QWeb est partagé entre facture et reçu.
        """
        self.ensure_one()
        if not self.fne_certified:
            raise UserError(_(
                "FNE : le ticket %s n'est pas certifié.\n\n"
                "Seul un ticket certifié auprès de la DGI peut être imprimé "
                "au format normalisé."
            ) % (self.name or ''))

        ICP = self.env['ir.config_parameter'].sudo()
        company = self.company_id
        partner = self.partner_id
        AccountMove = self.env['account.move']

        # --- Lignes, remises et ventilation des taxes ---
        # compute_all() est l'unique source fiable : pos.order ne produit pas
        # d'écritures de taxe avant la clôture de session.
        items = []
        total_ht_brut = 0.0
        total_remise = 0.0
        tax_amounts = {}
        tax_bases = {}
        for line in self.lines:
            quantity = abs(line.qty)
            gross = quantity * line.price_unit
            discount = line.discount or 0.0
            total_ht_brut += gross
            total_remise += gross * discount / 100.0
            items.append({
                'reference': line.product_id.default_code or '',
                'description': line.full_product_name or line.product_id.display_name or '',
                'price_unit': line.price_unit,
                'quantity': quantity,
                'uom': line.product_uom_id.name or '',
                'taxes': ', '.join(self._fne_tax_label(t) for t in line.tax_ids),
                'discount': discount,
                'subtotal': abs(line.price_subtotal),
            })
            if not line.tax_ids:
                continue
            computed = line.tax_ids.compute_all(
                line.price_unit * (1 - discount / 100.0),
                currency=self.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=partner,
            )
            for tax_detail in computed['taxes']:
                tax_id = tax_detail['id']
                tax_amounts[tax_id] = tax_amounts.get(tax_id, 0.0) + tax_detail['amount']
                tax_bases[tax_id] = tax_bases.get(tax_id, 0.0) + tax_detail['base']

        tax_summary = []
        total_tva = 0.0
        for tax in self.env['account.tax'].browse(tax_amounts.keys()):
            amount = tax_amounts[tax.id]
            group_name = tax.tax_group_id.name or ''
            if group_name and tax.name not in group_name:
                category = '%s - %s' % (group_name, tax.name)
            else:
                category = group_name or tax.name
            tax_summary.append({
                'category': category,
                'base': tax_bases.get(tax.id, 0.0),
                'rate': tax.amount,
                'amount': amount,
            })
            if tax.amount_type == 'percent' and tax.amount in FNE_VAT_RATES:
                total_tva += amount

        total_ht_net = self.amount_total - self.amount_tax
        total_autres_taxes = self.amount_tax - total_tva

        certification_date = ''
        if self.fne_certification_date:
            certification_date = fields.Datetime.context_timestamp(
                self, self.fne_certification_date
            ).strftime('%d/%m/%Y %H:%M:%S')
        order_date = self.date_order and fields.Datetime.context_timestamp(
            self, self.date_order
        ).strftime('%d/%m/%Y') or ''

        totals = [
            {'label': _("TOTAL HT"), 'value': total_ht_brut, 'strong': False},
            {'label': _("REMISE"), 'value': total_remise, 'strong': False},
            {'label': _("TOTAL HT APRÈS REMISE"), 'value': total_ht_net, 'strong': False},
            {'label': _("TVA"), 'value': total_tva, 'strong': False},
            {'label': _("TOTAL TTC"), 'value': total_ht_net + total_tva, 'strong': False},
            {'label': _("AUTRES TAXES"), 'value': total_autres_taxes, 'strong': False},
            {'label': _("TOTAL A PAYER"), 'value': self.amount_total, 'strong': True},
        ]

        return {
            # En-tête émetteur
            'company_name': company.name,
            'company_ncc': self.fne_ncc or ICP.get_param('l10n_ci_fne.ncc', ''),
            'company_tax_regime': ICP.get_param('l10n_ci_fne.tax_regime', ''),
            'company_tax_center': ICP.get_param('l10n_ci_fne.tax_center', ''),
            'company_rccm': company.company_registry or '',
            'establishment': ICP.get_param('l10n_ci_fne.establishment', '') or company.name,
            'company_address': AccountMove._fne_format_address(company.partner_id),
            'company_phone': company.phone or '',
            'company_email': company.email or '',
            # Ce qui a été transmis à la DGI, pas le nom du POS Odoo.
            'point_of_sale': self.config_id._get_fne_point_of_sale(),
            'certification_date': certification_date,
            'payment_method': self.fne_payment_method or '',
            'erp_number': self.name or '',
            'erp_date': order_date,
            # Identité du document
            'document_title': _("Reçu de caisse"),
            'fne_reference': self.fne_reference or '',
            # Client
            'client_name': partner.name or _("Client divers"),
            'client_address': (partner and AccountMove._fne_format_address(partner))
                              or (partner.email if partner else '') or '',
            'client_ncc': (partner.ncc or partner.vat or '') if partner else '',
            'client_tax_regime': partner.fne_tax_regime if partner else '',
            # Corps
            'items': items,
            'tax_summary': tax_summary,
            'totals': totals,
            'totals_count': len(totals),
        }
