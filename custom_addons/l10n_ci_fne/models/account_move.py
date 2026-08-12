# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from . import fne_utils

_logger = logging.getLogger(__name__)

# Taux reconnus comme TVA par la plateforme FNE (cf. _get_fne_tax_type).
# Toute autre taxe est reportée dans la ligne « AUTRES TAXES » du modèle DGI.
FNE_VAT_RATES = (18.0, 9.0, 0.0)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # === Champs FNE ===
    fne_reference = fields.Char(
        string="Référence FNE",
        readonly=True,
        copy=False,
        help="Numéro de facture normalisée attribué par la DGI"
    )
    fne_token = fields.Char(
        string="Token FNE",
        readonly=True,
        copy=False,
        help="URL de vérification FNE pour le QR Code"
    )
    fne_qr_code = fields.Binary(
        string="QR Code FNE",
        compute='_compute_fne_qr_code',
        store=True,
        copy=False,
        help="QR Code de vérification FNE"
    )
    fne_certified = fields.Boolean(
        string="Certifiée FNE",
        readonly=True,
        copy=False,
        default=False,
    )
    fne_invoice_id = fields.Char(
        string="ID Facture FNE",
        readonly=True,
        copy=False,
        help="Identifiant interne de la facture sur la plateforme FNE"
    )
    fne_ncc = fields.Char(
        string="NCC Entreprise",
        readonly=True,
        copy=False,
    )
    fne_balance_sticker = fields.Integer(
        string="Solde Stickers FNE",
        readonly=True,
        copy=False,
    )
    fne_certification_date = fields.Datetime(
        string="Date de certification",
        readonly=True,
        copy=False,
    )
    fne_error_message = fields.Text(
        string="Erreur FNE",
        readonly=True,
        copy=False,
    )
    fne_simulation = fields.Boolean(
        string="Certification simulation",
        readonly=True,
        copy=False,
        default=False,
        help="Indique que la certification a été faite en mode simulation (non envoyée à la DGI)"
    )
    fne_payment_method = fields.Char(
        string="Mode de paiement FNE",
        readonly=True,
        copy=False,
        help="Mode de paiement transmis à la DGI lors de la certification"
    )
    # Champs liés (non stockés) : la facture d'origine reste la source de
    # vérité, un avoir recertifié après coup reste ainsi cohérent.
    fne_origin_invoice = fields.Char(
        string="Facture d'origine",
        related='reversed_entry_id.name',
        readonly=True,
        help="Facture que cet avoir extourne."
    )
    fne_origin_reference = fields.Char(
        string="Référence FNE d'origine",
        related='reversed_entry_id.fne_reference',
        readonly=True,
        help="Numéro de facture normalisée de la facture extournée par cet avoir."
    )
    fne_is_rne = fields.Boolean(
        string="Rattachée à un reçu",
        copy=False,
        help="Cocher lorsque cette facture est émise en régularisation d'un "
             "reçu normalisé (ticket de caisse) déjà transmis à la DGI. "
             "Évite que la même transaction soit normalisée deux fois."
    )
    fne_rne_number = fields.Char(
        string="N° du reçu (RNE)",
        copy=False,
        help="Numéro du reçu normalisé pour lequel cette facture est émise."
    )

    @api.constrains('fne_is_rne', 'fne_rne_number')
    def _check_fne_rne_number(self):
        """La DGI rend le numéro de reçu obligatoire dès que isRne est vrai."""
        for move in self:
            if move.fne_is_rne and not (move.fne_rne_number or '').strip():
                raise ValidationError(_(
                    "FNE : le numéro du reçu est obligatoire lorsque la facture "
                    "est rattachée à un reçu normalisé."
                ))

    @api.depends('fne_token')
    def _compute_fne_qr_code(self):
        """Génère le QR Code à partir du token FNE"""
        for move in self:
            move.fne_qr_code = fne_utils.generate_qr_code(move.fne_token)

    def _post(self, soft=True):
        """Override pour certifier la facture FNE lors de la validation"""
        posted = super()._post(soft=soft)

        # Vérifier si la certification auto est activée
        ICP = self.env['ir.config_parameter'].sudo()
        auto_certify = ICP.get_param('l10n_ci_fne.auto_certify', 'False')

        if auto_certify == 'True':
            for move in posted:
                if move.move_type in ('out_invoice', 'out_refund') and not move.fne_certified:
                    try:
                        move._fne_certify()
                    except UserError as e:
                        # Ne pas bloquer la validation, juste logger l'erreur
                        move.fne_error_message = str(e)
                        _logger.warning("FNE: Certification échouée pour %s: %s", move.name, e)

        return posted

    def _fne_certify(self):
        """Certifie la facture auprès de la plateforme FNE"""
        self.ensure_one()

        if self.fne_certified:
            raise UserError(_("Cette facture est déjà certifiée FNE."))

        fne_api = self.env['l10n_ci_fne.api']
        payment_method = fne_api._get_payment_method(self)

        if self.move_type == 'out_invoice':
            result = fne_api.certify_invoice(self)
        elif self.move_type == 'out_refund':
            # Chercher la facture d'origine
            origin_move = self.reversed_entry_id
            if origin_move and origin_move.fne_invoice_id:
                # L'avoir reprend le mode de paiement de la facture d'origine :
                # l'endpoint /refund ne transmet que les quantités.
                payment_method = origin_move.fne_payment_method or payment_method
                result = fne_api.certify_refund(self, origin_move.fne_invoice_id)
            else:
                raise UserError(_(
                    "FNE: Impossible de certifier l'avoir. "
                    "La facture d'origine n'a pas été certifiée FNE."
                ))
        else:
            return

        if result.get('success'):
            invoice_data = result.get('invoice_data', {})
            self.write({
                'fne_reference': result.get('reference', ''),
                'fne_token': result.get('token', ''),
                'fne_ncc': result.get('ncc', ''),
                'fne_balance_sticker': result.get('balance_sticker', 0),
                'fne_invoice_id': invoice_data.get('id', ''),
                'fne_certified': True,
                'fne_simulation': result.get('simulation', False),
                'fne_certification_date': fields.Datetime.now(),
                'fne_payment_method': payment_method,
                'fne_error_message': False,
            })
            # Stocker les IDs FNE des items sur les lignes de facture
            fne_items = invoice_data.get('items', [])
            product_lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            for idx, line in enumerate(product_lines):
                if idx < len(fne_items):
                    line.fne_item_id = fne_items[idx].get('id', '')

    def action_fne_certify(self):
        """Action manuelle pour certifier une facture FNE"""
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("Seule une facture validée peut être certifiée FNE."))
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Seules les factures clients et avoirs peuvent être certifiés FNE."))
        self._fne_certify()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _('Facture certifiée FNE: %s') % self.fne_reference,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_fne_reset_simulation(self):
        """Réinitialise la certification simulation pour permettre une vraie certification"""
        self.ensure_one()
        if not self.fne_simulation:
            raise UserError(_("Cette facture n'a pas été certifiée en mode simulation."))
        self.write({
            'fne_reference': False,
            'fne_token': False,
            'fne_ncc': False,
            'fne_balance_sticker': 0,
            'fne_invoice_id': False,
            'fne_certified': False,
            'fne_simulation': False,
            'fne_certification_date': False,
            'fne_payment_method': False,
            'fne_error_message': False,
        })

    # ------------------------------------------------------------------
    # Impression au format Facture Normalisée Électronique
    # ------------------------------------------------------------------

    def _fne_format_amount(self, amount):
        """Montant au format du portail FNE, dans la précision de la devise."""
        self.ensure_one()
        return fne_utils.format_amount(amount, self.currency_id.decimal_places or 0)

    @api.model
    def _fne_format_rate(self, rate):
        """18.0 -> '18', 9.5 -> '9.5'"""
        return fne_utils.format_rate(rate)

    @api.model
    def _fne_format_quantity(self, quantity):
        """Quantité : jusqu'à 3 décimales, zéros finaux supprimés."""
        return fne_utils.format_quantity(quantity)

    @api.model
    def _fne_format_address(self, partner):
        """Adresse sur une seule ligne, comme sur le modèle DGI."""
        city_line = ' '.join(p for p in (partner.zip, partner.city) if p)
        parts = (partner.street, partner.street2, city_line,
                 partner.country_id.name if partner.country_id else '')
        return ' '.join(p.strip() for p in parts if p and p.strip())

    def _fne_tax_label(self, tax):
        """Libellé de taxe affiché dans la colonne « Taxes (%) » : code FNE
        pour les taux TVA reconnus, nom de la taxe Odoo sinon."""
        if tax.amount_type == 'percent' and tax.amount in FNE_VAT_RATES:
            code = self.env['l10n_ci_fne.api']._get_fne_tax_type(tax.amount)
        else:
            code = tax.name or 'TAXE'
        return '%s (%s)' % (code, self._fne_format_rate(tax.amount))

    def _fne_get_report_data(self):
        """Assemble toutes les données du modèle de facture normalisée DGI.

        Retourne un dict consommé par le template QWeb ; toute la logique de
        calcul est ici pour garder le template déclaratif.
        """
        self.ensure_one()
        if not self.fne_certified:
            raise UserError(_(
                "FNE : la facture %s n'est pas certifiée.\n\n"
                "Seule une facture certifiée auprès de la DGI peut être imprimée "
                "au format Facture Normalisée Électronique."
            ) % (self.name or ''))

        ICP = self.env['ir.config_parameter'].sudo()
        company = self.company_id
        partner = self.partner_id
        product_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        )

        # --- Lignes d'articles + total HT brut / remise ---
        items = []
        total_ht_brut = 0.0
        total_remise = 0.0
        for line in product_lines:
            quantity = abs(line.quantity)
            gross = quantity * line.price_unit
            discount = line.discount or 0.0
            total_ht_brut += gross
            total_remise += gross * discount / 100.0
            items.append({
                'reference': line.product_id.default_code or '',
                'description': line.name or line.product_id.display_name or '',
                'price_unit': line.price_unit,
                'quantity': quantity,
                'uom': line.product_uom_id.name or '',
                'taxes': ', '.join(self._fne_tax_label(t) for t in line.tax_ids),
                'discount': discount,
                'subtotal': abs(line.price_subtotal),
            })

        # --- Ventilation par taxe ---
        # Montant : agrégé depuis les écritures de taxe (source de vérité Odoo).
        # Base : somme des sous-totaux des lignes portant la taxe, ce qui évite
        # le double comptage quand une taxe a plusieurs lignes de répartition.
        amount_by_tax = {}
        for tax_line in self.line_ids.filtered(lambda l: l.tax_line_id):
            # direction_sign vaut -1 sur les factures clients (écritures de taxe
            # au crédit) et +1 sur les avoirs : le produit redonne un montant
            # de taxe positif dans les deux cas.
            amount = tax_line.amount_currency * self.direction_sign
            amount_by_tax[tax_line.tax_line_id.id] = \
                amount_by_tax.get(tax_line.tax_line_id.id, 0.0) + amount

        tax_summary = []
        total_tva = 0.0
        for tax in product_lines.tax_ids:
            if tax.id not in amount_by_tax:
                continue
            base = sum(
                abs(l.price_subtotal) for l in product_lines if tax in l.tax_ids
            )
            amount = amount_by_tax[tax.id]
            # « Groupe - Taxe », sauf quand le nom de la taxe est déjà contenu
            # dans celui du groupe (ex: groupe « T.V.A. 18% », taxe « 18% »).
            group_name = tax.tax_group_id.name or ''
            if group_name and tax.name not in group_name:
                category = '%s - %s' % (group_name, tax.name)
            else:
                category = group_name or tax.name
            tax_summary.append({
                'category': category,
                'base': base,
                'rate': tax.amount,
                'amount': amount,
            })
            if tax.amount_type == 'percent' and tax.amount in FNE_VAT_RATES:
                total_tva += amount

        # AUTRES TAXES est déduit du total de taxes Odoo pour que
        # TOTAL A PAYER reste toujours égal au total de la facture.
        total_autres_taxes = self.amount_tax - total_tva

        # Dates formatées en Python : le modèle DGI impose jj/mm/aaaa, quelle
        # que soit la langue de l'utilisateur qui imprime.
        certification_date = ''
        if self.fne_certification_date:
            certification_date = fields.Datetime.context_timestamp(
                self, self.fne_certification_date
            ).strftime('%d/%m/%Y %H:%M:%S')
        erp_date = self.invoice_date.strftime('%d/%m/%Y') if self.invoice_date else ''

        totals = [
            {'label': _("TOTAL HT"), 'value': total_ht_brut, 'strong': False},
            {'label': _("REMISE"), 'value': total_remise, 'strong': False},
            {'label': _("TOTAL HT APRÈS REMISE"), 'value': self.amount_untaxed, 'strong': False},
            {'label': _("TVA"), 'value': total_tva, 'strong': False},
            {'label': _("TOTAL TTC"), 'value': self.amount_untaxed + total_tva, 'strong': False},
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
            'company_address': self._fne_format_address(company.partner_id),
            'company_phone': company.phone or '',
            'company_email': company.email or '',
            'point_of_sale': ICP.get_param('l10n_ci_fne.point_of_sale', ''),
            'certification_date': certification_date,
            'payment_method': self.fne_payment_method or '',
            'erp_number': self.name or '',
            'erp_date': erp_date,
            # Identité du document
            'document_title': _("Facture d'avoir") if self.move_type == 'out_refund'
                              else _("Facture de vente"),
            'fne_reference': self.fne_reference or '',
            # Client
            'client_name': partner.name or '',
            'client_address': self._fne_format_address(partner) or partner.email or '',
            'client_ncc': partner.ncc or partner.vat or '',
            'client_tax_regime': partner.fne_tax_regime or '',
            # Corps
            'items': items,
            'tax_summary': tax_summary,
            'totals': totals,
            'totals_count': len(totals),
        }

    def action_fne_print_invoice(self):
        """Imprime la facture au format normalisé DGI."""
        self.ensure_one()
        return self.env.ref(
            'l10n_ci_fne.action_report_invoice_fne'
        ).report_action(self)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    fne_item_id = fields.Char(
        string="ID Article FNE",
        readonly=True,
        copy=False,
        help="Identifiant de l'article sur la plateforme FNE"
    )
