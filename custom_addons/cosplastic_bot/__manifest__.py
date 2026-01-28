# -*- coding: utf-8 -*-
{
    'name': "Coplastic AI Bot",

    'summary': "Améliore OdooBot avec ChatGPT et RAG pour des réponses intelligentes",

    'description': """
        CoplasticBot - OdooBot amélioré par l'IA
        ========================================

        Ce module étend OdooBot avec l'intelligence artificielle ChatGPT :
        - Réponses intelligentes aux questions des utilisateurs
        - RAG (Retrieval-Augmented Generation) avec la documentation Odoo 17
        - Assistant OpenAI intégré pour des réponses contextuelles
        - Commandes slash personnalisées (/aide, /devis, /client, etc.)
        - Configuration simple dans Paramètres → Paramètres Généraux

        L'utilisateur pose ses questions à OdooBot comme d'habitude,
        et les réponses sont générées par ChatGPT enrichi avec la doc Odoo.
    """,

    'author': "Coplastic",
    'website': "https://adriennde.com",
    'category': 'Productivity',
    'version': '17.0.2.0.0',
    'license': 'LGPL-3',

    'depends': ['base', 'base_setup', 'mail', 'mail_bot'],

    'external_dependencies': {'python': ['openai']},

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/openai_assistant_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'cosplastic_bot/static/src/js/channel_commands.js',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}
