# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ci_smig = fields.Float(
        string="SMIG mensuel (FCFA)",
        default=75000.0,
        help="Salaire Minimum Interprofessionnel Garanti mensuel en Côte d'Ivoire. "
             "Utilisé comme base de calcul des cotisations CNPS.",
    )
