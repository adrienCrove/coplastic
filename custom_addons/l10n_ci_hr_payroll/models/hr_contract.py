# -*- coding: utf-8 -*-

from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_ci_sursalaire = fields.Monetary(
        string="Sursalaire",
        help="Complément de salaire au-delà du salaire de base catégoriel",
        tracking=True,
    )
    l10n_ci_prime_transport = fields.Monetary(
        string="Prime de transport",
        default=30000,
        help="Prime de transport mensuelle (30 000 FCFA par défaut pour Abidjan)",
        tracking=True,
    )
    l10n_ci_taux_anciennete = fields.Float(
        string="Taux d'ancienneté (%)",
        default=0.0,
        help="Pourcentage de la prime d'ancienneté appliqué sur le salaire de base. "
             "Convention CI : 2% par an après 2 ans, plafonné à 25%",
        tracking=True,
    )
    l10n_ci_indemnite_conge = fields.Monetary(
        string="Indemnité de congé journalière",
        help="Montant journalier pour le calcul de l'allocation de congé payé",
        tracking=True,
    )
    l10n_ci_horaire_mensuel = fields.Float(
        string="Horaire mensuel",
        default=173.33,
        help="Nombre d'heures mensuelles (173.33h = 40h/semaine)",
    )
