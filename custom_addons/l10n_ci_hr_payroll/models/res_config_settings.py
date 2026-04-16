# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ci_smig = fields.Float(
        string="SMIG mensuel (FCFA)",
        related='company_id.l10n_ci_smig',
        readonly=False,
        help="Salaire Minimum Interprofessionnel Garanti — base de calcul CNPS.",
    )
    l10n_ci_check_contract_dates = fields.Boolean(
        string="Bloquer les bulletins hors période de contrat",
        config_parameter='l10n_ci_hr_payroll.check_contract_dates',
        help="Si activé, empêche de confirmer un bulletin de paie dont la période "
             "est antérieure à la date de début du contrat de l'employé.",
    )
