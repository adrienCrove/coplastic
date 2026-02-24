# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ci_cnps_number = fields.Char(
        string="N° CNPS",
        help="Numéro d'immatriculation CNPS de l'employé",
        groups="hr.group_hr_user",
    )
    l10n_ci_matricule = fields.Char(
        string="Matricule interne",
        groups="hr.group_hr_user",
    )
    l10n_ci_categorie = fields.Char(
        string="Catégorie",
        help="Catégorie professionnelle (ex: 8B, 6A, etc.)",
        groups="hr.group_hr_user",
    )
    l10n_ci_qualification = fields.Selection([
        ('manoeuvre', 'Manoeuvre'),
        ('ouvrier', 'Ouvrier'),
        ('employe', 'Employé'),
        ('agent_maitrise', 'Agent de Maîtrise'),
        ('maitrise', 'Maîtrise'),
        ('cadre', 'Cadre'),
        ('cadre_superieur', 'Cadre Supérieur'),
    ], string="Qualification",
        groups="hr.group_hr_user",
    )
    l10n_ci_parts_igr = fields.Float(
        string="Parts IGR",
        default=1.0,
        help="Nombre de parts pour l'Impôt Général sur le Revenu. "
             "1.0 = célibataire sans enfant, "
             "2.0 = marié sans enfant, "
             "+0.5 par enfant à charge",
        groups="hr.group_hr_user",
    )
    l10n_ci_nb_children = fields.Integer(
        string="Nb. enfants à charge",
        default=0,
        groups="hr.group_hr_user",
    )
    l10n_ci_bank_name = fields.Char(
        string="Banque",
        groups="hr.group_hr_user",
    )
    l10n_ci_bank_account = fields.Char(
        string="N° de compte bancaire",
        groups="hr.group_hr_user",
    )
    l10n_ci_convention = fields.Char(
        string="Convention Collective",
        default="Convention Collective Interprofessionnelle",
        groups="hr.group_hr_user",
    )
