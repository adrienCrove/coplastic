# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # === Configuration FNE ===
    l10n_ci_fne_api_key = fields.Char(
        string="Clé API FNE",
        config_parameter='l10n_ci_fne.api_key',
        help="Clé API fournie par la DGI dans votre espace FNE"
    )
    l10n_ci_fne_api_url = fields.Char(
        string="URL API FNE",
        config_parameter='l10n_ci_fne.api_url',
        help="URL de l'API FNE fournie par la DGI"
    )
    l10n_ci_fne_ncc = fields.Char(
        string="NCC Entreprise",
        config_parameter='l10n_ci_fne.ncc',
        help="Numéro de Compte Contribuable de votre entreprise"
    )
    l10n_ci_fne_point_of_sale = fields.Char(
        string="Point de vente",
        config_parameter='l10n_ci_fne.point_of_sale',
        default='1',
        help="Identifiant du point de vente"
    )
    l10n_ci_fne_establishment = fields.Char(
        string="Établissement",
        config_parameter='l10n_ci_fne.establishment',
        help="Nom de l'établissement"
    )
    l10n_ci_fne_auto_certify = fields.Boolean(
        string="Certification automatique",
        config_parameter='l10n_ci_fne.auto_certify',
        default=False,
        help="Certifier automatiquement les factures lors de la validation. "
             "ATTENTION : chaque certification consomme un sticker FNE."
    )
    l10n_ci_fne_simulation = fields.Boolean(
        string="Mode simulation",
        config_parameter='l10n_ci_fne.simulation',
        default=True,
        help="En mode simulation, les requêtes sont préparées et loguées "
             "mais PAS envoyées à la DGI. Utile pour vérifier les données avant la mise en production."
    )
