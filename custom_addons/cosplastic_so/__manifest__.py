# -*- coding: utf-8 -*-
{
    'name': "Coplastic - Ventes",

    'summary': "Personnalisation des devis et bons de commande Coplastic",

    'description': """
        - Validité des devis par défaut : 14 jours
        - Conditions de paiement 60 et 90 jours
        - Lignes de commande en lecture seule après confirmation
        - Protection contre la suppression (admin uniquement)
    """,

    'author': "Coplastic",
    'website': "https://www.coplastique.com",

    'category': 'Sales',
    'version': '17.0.2.0.0',
    'license': 'LGPL-3',

    'depends': ['sale', 'account', 'stock'],

    'data': [
        'security/ir.model.access.csv',
        'data/payment_terms.xml',
        'views/sale_stock_check_wizard_views.xml',
        'views/views.xml',
        'reports/report_proforma.xml',
    ],
}
