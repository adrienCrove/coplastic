# -*- coding: utf-8 -*-

import logging

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FneApiService(models.AbstractModel):
    _inherit = 'l10n_ci_fne.api'

    def _prepare_pos_order_items(self, order):
        """Lignes du ticket au format FNE."""
        items = []
        for line in order.lines:
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
                'description': line.full_product_name or line.product_id.name or 'Article',
                'quantity': abs(line.qty),
                'amount': line.price_unit,
                'discount': line.discount or 0,
                'measurementUnit': line.product_uom_id.name or 'unité',
            }

            if custom_taxes:
                item['customTaxes'] = custom_taxes

            items.append(item)
        return items

    def _prepare_pos_order_payload(self, order):
        """Corps de la requête de certification d'un ticket de caisse.

        Reprend le schéma documenté pour les factures : la plateforme FNE
        n'expose qu'une route de signature, seul le contenu diffère.

        Un document émis au point de vente est un reçu normalisé (RNE) :
        `isRne` est vrai et `rne` porte le numéro de reçu de la caisse. C'est
        ce numéro qu'une facture de régularisation reprendra ensuite dans son
        propre champ `rne` pour s'y rattacher.
        """
        config = self._get_config()
        partner = order.partner_id
        # Sans client identifié, un ticket de caisse est une vente au
        # particulier : B2C, sans NCC.
        template = self._get_template_type(partner) if partner else 'B2C'

        payload = {
            'invoiceType': 'sale',
            'paymentMethod': order._fne_get_payment_method(),
            'template': template,
            'isRne': True,
            'rne': order._fne_get_receipt_number(),
            'clientCompanyName': (partner.name if partner else '') or 'CLIENT DIVERS',
            'clientPhone': (partner.phone or partner.mobile if partner else '') or '0000000000',
            'clientEmail': (partner.email if partner else '') or '',
            'clientSellerName': order.user_id.name or order.employee_id.name or '',
            # La DGI valide ce champ contre les points de vente déclarés sur le
            # compte : le nom du POS Odoo n'y correspond pas nécessairement.
            'pointOfSale': order.config_id._get_fne_point_of_sale(),
            'establishment': config.get('establishment', ''),
            'commercialMessage': '',
            'footer': '',
            'foreignCurrency': '',
            'foreignCurrencyRate': 0,
            'items': self._prepare_pos_order_items(order),
            'discount': 0,
        }

        if template in ('B2B', 'B2G') and partner:
            client_ncc = self._get_client_ncc(partner)
            if client_ncc:
                payload['clientNcc'] = client_ncc

        return payload

    def _validate_pos_order_for_fne(self, order):
        """Contrôles préalables à la certification d'un ticket."""
        if not order.lines:
            raise UserError(_("FNE : le ticket doit contenir au moins une ligne."))

        partner = order.partner_id
        if partner and self._get_template_type(partner) == 'B2B':
            if not self._get_client_ncc(partner):
                raise UserError(_(
                    "FNE - NCC obligatoire pour B2B :\n"
                    "Le client '%s' est une entreprise. Renseignez son NCC "
                    "dans sa fiche, ou retirez-le du ticket pour une vente "
                    "au particulier."
                ) % partner.name)
        return True

    def certify_pos_order(self, order):
        """Certifie un ticket de caisse auprès de la plateforme FNE."""
        self._validate_pos_order_for_fne(order)
        payload = self._prepare_pos_order_payload(order)
        return self._sign_document(payload, order.name)
