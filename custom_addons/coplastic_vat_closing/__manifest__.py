# -*- coding: utf-8 -*-
{
    'name': 'Coplastic - Clôture & Déclaration TVA',
    'version': '17.0.1.0.0',
    'summary': "Déclaration TVA périodique + écriture de clôture et report du crédit (SYSCOHADA CI)",
    'description': """
Déclaration / Clôture de TVA pour Odoo Community (SYSCOHADA / Côte d'Ivoire).

Calcule pour une période :
- la TVA collectée (compte 443100),
- la TVA déductible (comptes 445xxx),
- le crédit de TVA reporté de la période précédente (compte 444900),
et génère l'écriture de clôture (en brouillon) qui solde ces comptes et
constate soit la TVA à décaisser (444100), soit le nouveau crédit à reporter (444900).

Remplace l'automatisme de clôture TVA réservé à Odoo Enterprise.
""",
    'category': 'Accounting/Accounting',
    'author': 'Coplastic',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/vat_closing_data.xml',
        'views/vat_closing_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
