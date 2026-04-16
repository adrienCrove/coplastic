# -*- coding: utf-8 -*-
{
    'name': "Paie - Côte d'Ivoire",
    'summary': "Localisation paie pour la Côte d'Ivoire (CNPS, ITS, CMU)",
    'description': """
        Module de localisation de la paie pour la Côte d'Ivoire.

        Inclut :
        - Structure salariale conforme à la Convention Collective Interprofessionnelle
        - Règles de calcul CNPS (Retraite, Prestations Familiales, Accident du Travail)
        - Barème ITS (Impôt sur Traitements et Salaires)
        - Prélèvement CMU
        - Taxes patronales (Taxe d'Apprentissage, Formation Professionnelle Continue)
        - Prime de transport Abidjan
        - Champs spécifiques CI sur employé et contrat
        - Bulletin de paie au format ivoirien
    """,
    'author': "Coplastic",
    'website': "https://coplastic.adriennde.com",
    'category': 'Human Resources/Payroll',
    'version': '17.0.1.0.0',
    'depends': [
        'payroll',
        'payroll_account',
        'hr_contract',
        'report_xlsx',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_salary_rule_category.xml',
        'data/hr_contribution_register.xml',
        'data/hr_salary_rules.xml',
        'data/hr_payroll_structure.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/res_config_settings_views.xml',
        'report/report_payslip_ci.xml',
        'report/report_payroll_book.xml',
        'wizard/payroll_book_wizard.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
