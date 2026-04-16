# -*- coding: utf-8 -*-
{
    'name': 'Avance sur Salaire - Côte d\'Ivoire',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestion des avances sur salaire avec workflow de validation et remboursement multi-mois',
    'description': """
        Gestion avancée des avances sur salaire :
        - Demande d'avance par l'employé
        - Workflow de validation (brouillon → confirmé → approuvé → remboursé)
        - Remboursement en plusieurs mensualités
        - Intégration automatique dans le bulletin de paie
        - Suivi du solde restant
    """,
    'author': 'Coplastic',
    'depends': ['l10n_ci_hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/hr_salary_advance_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
