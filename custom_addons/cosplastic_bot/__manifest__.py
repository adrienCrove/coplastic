# -*- coding: utf-8 -*-
{
    'name': "Coplastic AI Bot",

    'summary': "Améliore OdooBot avec ChatGPT pour des réponses intelligentes",

    'description': """
        CoplasticBot - OdooBot amélioré par l'IA
        ========================================

        Ce module étend OdooBot avec l'intelligence artificielle ChatGPT :
        - Réponses intelligentes aux questions des utilisateurs
        - Aide contextuelle sur l'utilisation d'Odoo
        - Configuration simple dans Paramètres → Paramètres Généraux

        L'utilisateur pose ses questions à OdooBot comme d'habitude,
        et les réponses sont générées par ChatGPT.
    """,

    'author': "Coplastic",
    'website': "https://coplastic.adriennde.com",
    'category': 'Productivity',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    'depends': ['base', 'base_setup', 'mail', 'mail_bot'],

    'external_dependencies': {'python': ['openai']},

    'data': [
        'views/res_config_settings_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
