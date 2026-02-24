# -*- coding: utf-8 -*-

import json
import logging
import requests

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Mapping des méthodes de paiement Odoo → FNE
PAYMENT_METHOD_MAP = {
    'cash': 'cash',
    'bank': 'transfer',
    'manual': 'transfer',
    'electronic': 'card',
    'check_printing': 'check',
}

# Mapping des taxes Odoo → FNE
TAX_TYPE_MAP = {
    18.0: 'TVA',    # TVA normal 18%
    9.0: 'TVAB',    # TVA réduit 9%
    0.0: 'TVAC',    # TVA exonéré convention 0%
}


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
            'simulation': ICP.get_param('l10n_ci_fne.simulation', 'True'),
        }
        return config

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

    def _get_template_type(self, partner):
        """Détermine le type de facturation B2B/B2C/B2G/B2F"""
        if partner.country_id and partner.country_id.code != 'CI':
            return 'B2F'
        if partner.company_type == 'company' and partner.vat:
            return 'B2B'
        if partner.company_type == 'company':
            return 'B2B'
        return 'B2C'

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
            'isRne': False,
            'rne': '',
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

        # B2B : NCC du client obligatoire
        if template == 'B2B' and partner.vat:
            payload['clientNcc'] = partner.vat

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
        config = self._get_config()
        payload = self._prepare_invoice_payload(invoice)

        # === MODE SIMULATION ===
        if config.get('simulation') == 'True':
            _logger.info(
                "FNE [SIMULATION]: Facture %s - Requête préparée (non envoyée)",
                invoice.name
            )
            _logger.info(
                "FNE [SIMULATION]: Payload:\n%s",
                json.dumps(payload, indent=2, ensure_ascii=False)
            )
            # Retourner des données fictives pour tester le flux
            return {
                'success': True,
                'reference': 'SIM-%s' % invoice.name,
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

        _logger.info("FNE: Certification facture %s - Endpoint: %s", invoice.name, endpoint)
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
                    "FNE: Facture %s certifiée - Réf: %s",
                    invoice.name,
                    data.get('reference', '')
                )
                return {
                    'success': True,
                    'reference': data.get('reference', ''),
                    'token': data.get('token', ''),
                    'ncc': data.get('ncc', ''),
                    'balance_sticker': data.get('balance_sticker', 0),
                    'invoice_data': data.get('invoice', {}),
                }
            elif response.status_code == 401:
                error_data = response.json()
                raise UserError(_(
                    "FNE: Erreur d'authentification - %s"
                ) % error_data.get('message', 'Clé API invalide'))
            elif response.status_code == 400:
                error_data = response.json()
                raise UserError(_(
                    "FNE: Erreur dans la requête - %s"
                ) % error_data.get('message', 'Données invalides'))
            else:
                raise UserError(_(
                    "FNE: Erreur serveur (code %s) - %s"
                ) % (response.status_code, response.text[:200]))

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

        # Préparer les items pour l'avoir
        items = []
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            # On a besoin de l'id FNE de l'item original
            # Pour simplifier, on envoie la quantité retournée
            items.append({
                'id': line.fne_item_id or '',
                'quantity': abs(line.quantity),
            })

        payload = {'items': items}

        _logger.info("FNE: Certification avoir %s - Endpoint: %s", invoice.name, endpoint)

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
                    'balance_sticker': data.get('balance_sticker', 0),
                }
            else:
                error_msg = response.text[:200]
                raise UserError(_("FNE: Erreur avoir (code %s) - %s") % (response.status_code, error_msg))

        except requests.exceptions.ConnectionError:
            raise UserError(_("FNE: Impossible de se connecter à la plateforme FNE."))
        except requests.exceptions.Timeout:
            raise UserError(_("FNE: Délai d'attente dépassé."))
