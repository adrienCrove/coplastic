# -*- coding: utf-8 -*-

import re
from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Régimes d'imposition de la DGI Côte d'Ivoire, tels qu'imprimés sur la
# facture normalisée électronique.
FNE_TAX_REGIMES = [
    ('RNI', "RNI - Réel Normal d'Imposition"),
    ('RSI', "RSI - Réel Simplifié d'Imposition"),
    ('RME', "RME - Régime des Microentreprises"),
    ('RE', "RE - Régime de l'Entreprenant"),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Champ NCC s'il n'existe pas déjà
    ncc = fields.Char(
        string="NCC",
        help="Numéro de Compte Contribuable (obligatoire pour B2B/FNE)"
    )

    fne_tax_regime = fields.Selection(
        FNE_TAX_REGIMES,
        string="Régime d'imposition",
        help="Régime d'imposition du client, imprimé sur la facture normalisée."
    )

    # Champ pour identifier les administrations publiques (B2G)
    fne_is_government = fields.Boolean(
        string="Administration publique",
        default=False,
        help="Cocher si ce client est une administration publique ou un organisme gouvernemental (B2G)."
    )

    # Champ calculé pour afficher l'alerte NCC manquant
    fne_ncc_warning = fields.Boolean(
        compute='_compute_fne_ncc_warning',
        string="Alerte NCC manquant"
    )

    @api.depends('is_company', 'company_type', 'vat', 'ncc')
    def _compute_fne_ncc_warning(self):
        for partner in self:
            ncc_value = partner.ncc or ''
            partner.fne_ncc_warning = (
                partner.is_company and
                not ncc_value and
                not partner.vat
            )

    @api.constrains('ncc')
    def _check_ncc_format(self):
        """Valide le format du NCC (Numéro de Compte Contribuable)
        Format attendu: 7 chiffres + 1 lettre majuscule (ex: 9809714J)
        """
        ncc_pattern = re.compile(r'^[0-9]{7}[A-Z]$')
        for partner in self:
            ncc_value = getattr(partner, 'ncc', None)
            if ncc_value:
                ncc_clean = ncc_value.strip().upper()
                if not ncc_pattern.match(ncc_clean):
                    raise ValidationError(
                        "Le NCC '%s' n'est pas valide.\n"
                        "Format attendu: 7 chiffres + 1 lettre majuscule\n"
                        "Exemple: 9809714J" % ncc_value
                    )

    def _get_client_ncc(self):
        """Récupère le NCC du partenaire"""
        return getattr(self, 'ncc', None) or self.vat or ''

    @api.onchange('is_company', 'company_type')
    def _onchange_company_type_fne_warning(self):
        """Affiche un avertissement quand on sélectionne Entreprise sans NCC"""
        if self.is_company and not self._get_client_ncc():
            return {
                'warning': {
                    'title': "NCC requis pour FNE",
                    'message': "Pour les entreprises (B2B), le NCC (Numéro de Compte Contribuable) "
                               "est obligatoire pour la certification FNE des factures.\n\n"
                               "Veuillez renseigner le NCC dans le champ prévu.",
                    'type': 'notification',
                }
            }
