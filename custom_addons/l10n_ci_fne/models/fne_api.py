# -*- coding: utf-8 -*-

import json
import logging
import requests

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

# Modes de paiement transmis à la DGI dans le champ `paymentMethod`.
# 'mobile-money' est attesté par la documentation officielle ; les autres
# proviennent du mapping historique du module et restent à confronter à la
# liste exhaustive de la DGI.
FNE_PAYMENT_METHODS = [
    ('cash', "Espèces"),
    ('card', "Carte bancaire"),
    ('mobile-money', "Mobile Money"),
    ('check', "Chèque"),
    ('transfer', "Virement"),
    ('deferred', "Paiement différé"),
]


class FneApiService(models.AbstractModel):
    _name = 'l10n_ci_fne.api'
    _description = 'Service API FNE DGI Côte d\'Ivoire'

    def _get_config(self):
        """Récupère la configuration FNE depuis les paramètres"""
        ICP = self.env['ir.config_parameter'].sudo()
        config = {
            'api_key': ICP.get_param('l10n_ci_fne.api_key', ''),
            'api_url': ICP.get_param('l10n_ci_fne.api_url', ''),
            'ncc': ICP.get_param('l10n_ci_fne.ncc', ''),
            'point_of_sale': ICP.get_param('l10n_ci_fne.point_of_sale', '1'),
            'establishment': ICP.get_param('l10n_ci_fne.establishment', ''),
            'auto_certify': ICP.get_param('l10n_ci_fne.auto_certify', 'False'),
            'simulation': ICP.get_param('l10n_ci_fne.simulation', 'False'),
        }
        return config

    def _format_api_error(self, response):
        """Message lisible à partir d'une réponse en échec de la plateforme.

        La DGI renvoie un `message` souvent générique (« Bad Request
        Exception ») et place le détail utile dans des clés annexes : on
        remonte tout ce qui est exploitable plutôt que le seul `message`.
        """
        try:
            data = response.json()
        except ValueError:
            return response.text[:800] or _("Réponse vide de la plateforme.")

        if not isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False)[:800]

        parts = []
        for key in ('message', 'error', 'detail', 'title', 'description'):
            value = data.get(key)
            if value and str(value) not in parts:
                parts.append(str(value))
        for key in ('errors', 'violations', 'details', 'fieldErrors', 'data'):
            value = data.get(key)
            if value:
                parts.append(json.dumps(value, ensure_ascii=False))

        return '\n'.join(parts)[:800] or json.dumps(data, ensure_ascii=False)[:800]

    def _get_headers(self, api_key):
        """Retourne les headers pour l'API FNE"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }

    def _get_fne_tax_type(self, tax_amount):
        """Détermine le type de taxe FNE selon le taux"""
        if tax_amount >= 18.0:
            return 'TVA'
        elif tax_amount >= 9.0:
            return 'TVAB'
        elif tax_amount == 0.0:
            return 'TVAC'
        return 'TVA'

    def _get_client_ncc(self, partner):
        """Récupère le NCC du client"""
        # Priorité: champ ncc dédié, sinon vat comme fallback
        return getattr(partner, 'ncc', None) or partner.vat or ''

    def _get_template_type(self, partner):
        """
        Détermine le type de facturation FNE:
        - B2F: Client étranger (pays différent de CI)
        - B2G: Administration publique / Gouvernement
        - B2B: Entreprise ivoirienne (NCC obligatoire)
        - B2C: Particulier ivoirien
        """
        # Client étranger → B2F
        if partner.country_id and partner.country_id.code != 'CI':
            return 'B2F'

        # Administration publique → B2G
        if getattr(partner, 'fne_is_government', False):
            return 'B2G'

        # Entreprise → B2B
        if partner.company_type == 'company' or partner.is_company:
            return 'B2B'

        # Particulier → B2C
        return 'B2C'

    def _validate_invoice_for_fne(self, invoice):
        """Valide que la facture peut être certifiée FNE"""
        partner = invoice.partner_id
        template = self._get_template_type(partner)

        # B2B: NCC client obligatoire
        if template == 'B2B':
            client_ncc = self._get_client_ncc(partner)
            if not client_ncc:
                raise UserError(_(
                    "FNE - NCC obligatoire pour B2B:\n"
                    "Le client '%s' est une entreprise (B2B).\n"
                    "Veuillez renseigner son NCC (Numéro de Compte Contribuable) "
                    "dans la fiche du contact."
                ) % partner.name)

        # Vérifier que le client a un nom
        if not partner.name:
            raise UserError(_("FNE: Le client doit avoir un nom."))

        # Vérifier qu'il y a des lignes de facture
        lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        if not lines:
            raise UserError(_("FNE: La facture doit contenir au moins une ligne de produit."))

        return True

    def _get_payment_method(self, invoice):
        """Détermine la méthode de paiement FNE"""
        if invoice.invoice_payment_term_id:
            return 'deferred'
        return 'cash'

    def _prepare_invoice_items(self, invoice):
        """Prépare les lignes de facture au format FNE"""
        items = []
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            # Déterminer les taxes
            taxes = []
            custom_taxes = []
            for tax in line.tax_ids:
                if tax.amount in (18.0, 9.0, 0.0):
                    taxes.append(self._get_fne_tax_type(tax.amount))
                else:
                    custom_taxes.append({
                        'name': tax.name or 'TAXE',
                        'amount': tax.amount,
                    })

            if not taxes:
                taxes = ['TVA']

            item = {
                'taxes': taxes,
                'reference': line.product_id.default_code or '',
                'description': line.name or line.product_id.name or 'Article',
                'quantity': line.quantity,
                'amount': line.price_unit,
                'discount': line.discount or 0,
                'measurementUnit': line.product_uom_id.name or 'unité',
            }

            if custom_taxes:
                item['customTaxes'] = custom_taxes

            items.append(item)
        return items

    def _prepare_invoice_payload(self, invoice):
        """Prépare le corps de la requête pour la certification d'une facture"""
        config = self._get_config()
        partner = invoice.partner_id
        template = self._get_template_type(partner)

        payload = {
            'invoiceType': 'sale',
            'paymentMethod': self._get_payment_method(invoice),
            'template': template,
            # Rattachement à un reçu normalisé émis au point de vente : évite
            # que la transaction soit normalisée une seconde fois.
            'isRne': bool(invoice.fne_is_rne),
            'rne': (invoice.fne_rne_number or '').strip() if invoice.fne_is_rne else '',
            'clientCompanyName': partner.name or '',
            'clientPhone': partner.phone or partner.mobile or '0000000000',
            'clientEmail': partner.email or '',
            'clientSellerName': invoice.invoice_user_id.name or '',
            'pointOfSale': config.get('point_of_sale', '1'),
            'establishment': config.get('establishment', ''),
            'commercialMessage': '',
            'footer': '',
            'foreignCurrency': '',
            'foreignCurrencyRate': 0,
            'items': self._prepare_invoice_items(invoice),
            'discount': 0,
        }

        # B2B / B2G : NCC du client
        if template in ('B2B', 'B2G'):
            client_ncc = self._get_client_ncc(partner)
            if client_ncc:
                payload['clientNcc'] = client_ncc

        # B2F : devise étrangère
        if template == 'B2F' and invoice.currency_id.name != 'XOF':
            payload['foreignCurrency'] = invoice.currency_id.name
            # Taux de conversion vers XOF
            rate = invoice.currency_id.with_context(
                date=invoice.invoice_date
            ).rate
            if rate:
                payload['foreignCurrencyRate'] = round(1.0 / rate, 2)

        return payload

    def certify_invoice(self, invoice):
        """Certifie une facture auprès de la plateforme FNE"""
        # Validation préalable
        self._validate_invoice_for_fne(invoice)
        payload = self._prepare_invoice_payload(invoice)
        return self._sign_document(payload, invoice.name)

    def _sign_document(self, payload, label):
        """Signe un document auprès de la plateforme FNE.

        Partagé par les factures et les tickets de caisse : la route
        /external/invoices/sign et le format de réponse sont identiques,
        seul le contenu du payload change.

        :param label: nom du document, pour les logs et la référence simulée.
        """
        config = self._get_config()

        # === MODE SIMULATION ===
        if config.get('simulation') == 'True':
            _logger.info(
                "FNE [SIMULATION]: %s - Requête préparée (non envoyée)", label
            )
            _logger.info(
                "FNE [SIMULATION]: Payload:\n%s",
                json.dumps(payload, indent=2, ensure_ascii=False)
            )
            # Retourner des données fictives pour tester le flux
            return {
                'success': True,
                'reference': 'SIM-%s' % label,
                'token': '',
                'ncc': config.get('ncc', ''),
                'balance_sticker': 0,
                'invoice_data': {'id': 'simulation'},
                'simulation': True,
            }

        # === MODE PRODUCTION ===
        if not config.get('api_key'):
            raise UserError(_(
                "Clé API FNE non configurée. "
                "Allez dans Facturation → Configuration → Paramètres → FNE."
            ))

        if not config.get('api_url'):
            raise UserError(_(
                "URL de l'API FNE non configurée. "
                "Allez dans Facturation → Configuration → Paramètres → FNE."
            ))

        api_url = config['api_url'].rstrip('/')
        endpoint = f"{api_url}/external/invoices/sign"
        headers = self._get_headers(config['api_key'])

        _logger.info("FNE: Certification %s - Endpoint: %s", label, endpoint)
        _logger.info("FNE: Payload:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code in (200, 201):
                data = response.json()
                _logger.info(
                    "FNE: %s certifié - Réf: %s", label, data.get('reference', '')
                )
                # Log pour debug - voir les items retournés
                invoice_obj = data.get('invoice', {})
                items_list = invoice_obj.get('items', [])
                _logger.info("FNE: Invoice data contient %d items", len(items_list))
                for idx, item in enumerate(items_list):
                    _logger.info("FNE: Item %d - id=%s", idx, item.get('id', 'AUCUN'))
                return {
                    'success': True,
                    'reference': data.get('reference', ''),
                    'token': data.get('token', ''),
                    'ncc': data.get('ncc', ''),
                    'balance_sticker': data.get('balance_sticker', 0),
                    'invoice_data': data.get('invoice', {}),
                }
            # Toute réponse en échec est tracée intégralement : la plateforme
            # place souvent le détail des champs refusés hors du seul `message`.
            _logger.warning(
                "FNE: %s refusé (code %s) - Réponse brute:\n%s",
                label, response.status_code, response.text
            )
            if response.status_code == 401:
                raise UserError(_(
                    "FNE: Erreur d'authentification\n%s"
                ) % self._format_api_error(response))
            elif response.status_code == 400:
                raise UserError(_(
                    "FNE: Erreur dans la requête\n%s"
                ) % self._format_api_error(response))
            else:
                raise UserError(_(
                    "FNE: Erreur serveur (code %s)\n%s"
                ) % (response.status_code, self._format_api_error(response)))

        except requests.exceptions.ConnectionError:
            raise UserError(_(
                "FNE: Impossible de se connecter à la plateforme FNE. "
                "Vérifiez votre connexion internet et l'URL configurée."
            ))
        except requests.exceptions.Timeout:
            raise UserError(_(
                "FNE: Délai d'attente dépassé. "
                "La plateforme FNE ne répond pas."
            ))

    def _get_already_refunded_quantities(self, invoice, origin_move):
        """Quantités déjà avoirisées par article FNE sur la facture d'origine.

        Plusieurs avoirs partiels peuvent viser la même facture : le contrôle
        de quantité doit tenir compte de ceux déjà certifiés, sans quoi deux
        avoirs de la moitié passeraient là où un avoir entier serait refusé.
        Seuls les avoirs certifiés comptent — un brouillon n'a rien consommé
        auprès de la DGI.
        """
        quantities = {}
        if not origin_move:
            return quantities

        previous_refunds = self.env['account.move'].search([
            ('move_type', '=', 'out_refund'),
            ('reversed_entry_id', '=', origin_move.id),
            ('fne_certified', '=', True),
            ('id', '!=', invoice.id),
        ])
        origin_lines = origin_move.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        )
        for refund in previous_refunds:
            refund_lines = refund.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product'
            )
            for idx, line in enumerate(refund_lines):
                item_id = line.fne_item_id
                if not item_id and idx < len(origin_lines):
                    item_id = origin_lines[idx].fne_item_id
                if item_id:
                    quantities[item_id] = quantities.get(item_id, 0.0) + abs(line.quantity)
        return quantities

    def certify_refund(self, invoice, original_invoice_fne_id):
        """Certifie une facture d'avoir auprès de la plateforme FNE"""
        config = self._get_config()

        if not config.get('api_key') or not config.get('api_url'):
            raise UserError(_("Configuration FNE incomplète."))

        if not original_invoice_fne_id:
            raise UserError(_(
                "FNE: La facture d'origine n'a pas d'identifiant FNE. "
                "Impossible de créer l'avoir."
            ))

        api_url = config['api_url'].rstrip('/')
        endpoint = f"{api_url}/external/invoices/{original_invoice_fne_id}/refund"
        headers = self._get_headers(config['api_key'])

        # Récupérer les lignes de la facture originale pour obtenir les IDs FNE
        origin_move = invoice.reversed_entry_id
        origin_lines = origin_move.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product'
        ) if origin_move else []

        # Préparer les items pour l'avoir
        items = []
        refund_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')

        already_refunded = self._get_already_refunded_quantities(invoice, origin_move)

        for idx, line in enumerate(refund_lines):
            # Chercher l'ID FNE depuis la ligne de l'avoir ou depuis la facture originale
            fne_item_id = line.fne_item_id
            if not fne_item_id and idx < len(origin_lines):
                fne_item_id = origin_lines[idx].fne_item_id

            if not fne_item_id:
                raise UserError(_(
                    "FNE: L'article '%s' n'a pas d'identifiant FNE.\n"
                    "La facture originale doit avoir été certifiée avec les IDs des items stockés.\n"
                    "Veuillez contacter le support."
                ) % (line.name or line.product_id.name))

            # On ne peut pas rembourser plus que ce qui a été facturé : la
            # facture d'origine reste la référence, avoirs déjà certifiés
            # déduits.
            if idx < len(origin_lines):
                invoiced_qty = abs(origin_lines[idx].quantity)
                refunded_qty = already_refunded.get(fne_item_id, 0.0)
                remaining = invoiced_qty - refunded_qty
                if float_compare(
                    abs(line.quantity), remaining,
                    precision_rounding=line.product_uom_id.rounding or 0.01
                ) > 0:
                    raise UserError(_(
                        "FNE : quantité d'avoir trop élevée pour « %(product)s ».\n\n"
                        "Facturé sur %(origin)s : %(invoiced)s\n"
                        "Déjà avoirisé : %(refunded)s\n"
                        "Reste avoirisable : %(remaining)s\n"
                        "Demandé sur cet avoir : %(asked)s\n\n"
                        "Corrigez la quantité avant de certifier."
                    ) % {
                        'product': line.name or line.product_id.name,
                        'origin': origin_move.name,
                        'invoiced': invoiced_qty,
                        'refunded': refunded_qty,
                        'remaining': remaining,
                        'asked': abs(line.quantity),
                    })

            items.append({
                'id': fne_item_id,
                'quantity': abs(line.quantity),
            })

        payload = {'items': items}

        _logger.info("FNE: Certification avoir %s - Endpoint: %s", invoice.name, endpoint)
        _logger.info("FNE: Payload avoir:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code in (200, 201):
                data = response.json()
                _logger.info("FNE: Avoir %s certifié - Réf: %s", invoice.name, data.get('reference', ''))
                return {
                    'success': True,
                    'reference': data.get('reference', ''),
                    'token': data.get('token', ''),
                    # L'endpoint /refund ne renvoie pas systématiquement le NCC :
                    # il est constant pour l'entreprise, on le reprend de la
                    # configuration plutôt que de laisser le champ vide.
                    'ncc': data.get('ncc') or config.get('ncc', ''),
                    'balance_sticker': data.get('balance_sticker', 0),
                    'invoice_data': data.get('invoice', {}),
                }
            else:
                _logger.warning(
                    "FNE: Avoir %s refusé (code %s) - Réponse brute:\n%s",
                    invoice.name, response.status_code, response.text
                )
                raise UserError(_(
                    "FNE: Erreur avoir (code %s)\n%s"
                ) % (response.status_code, self._format_api_error(response)))

        except requests.exceptions.ConnectionError:
            raise UserError(_("FNE: Impossible de se connecter à la plateforme FNE."))
        except requests.exceptions.Timeout:
            raise UserError(_("FNE: Délai d'attente dépassé."))
