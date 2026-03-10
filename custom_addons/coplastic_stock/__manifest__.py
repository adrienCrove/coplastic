# -*- coding: utf-8 -*-
{
    'name': "Coplastic - Stock",

    'summary': "Suivi des impressions et alertes de stock",

    'description': """
        - Historique complet d'impression des bons de livraison (date/heure, utilisateur, numéro)
        - Alertes email quotidiennes pour les produits en pénurie de stock
    """,

    'author': "Coplastic",
    'website': "https://www.coplastique.com",

    'category': 'Inventory',
    'version': '17.0.2.0.0',
    'license': 'LGPL-3',

    'depends': ['stock'],

    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/views.xml',
        'views/res_config_settings_views.xml',
    ],
}
