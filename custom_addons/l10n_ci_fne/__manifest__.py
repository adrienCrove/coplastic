# -*- coding: utf-8 -*-
{
    'name': "Facturation Normalisée Électronique - Côte d'Ivoire",
    'summary': "Intégration API FNE/DGI pour la certification des factures en Côte d'Ivoire",
    'description': """
Module de Facturation Normalisée Électronique (FNE)
====================================================
Ce module intègre l'API de la Direction Générale des Impôts (DGI) de Côte d'Ivoire
pour la certification électronique des factures conformément à la loi de finances 2025.

Fonctionnalités :
- Certification automatique des factures lors de la validation
- Génération du QR Code de vérification
- Apposition du sticker FNE sur les factures PDF
- Gestion des factures d'avoir (refund)
- Numérotation FNE en série ininterrompue
    """,
    'author': "Coplastic",
    'website': "https://coplastic.adriennde.com",
    'category': 'Accounting/Localizations',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/fne_data.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice_fne.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
