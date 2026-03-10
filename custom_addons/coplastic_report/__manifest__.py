# -*- coding: utf-8 -*-
{
    'name': "Coplastic - Rapports personnalisés",

    'summary': "En-tête et pied de page personnalisés pour les rapports Coplastic",

    'description': """
        Personnalisation de la mise en page des rapports PDF :
        - Logo Coplastic centré en en-tête
        - Informations légales en pied de page
    """,

    'author': "Coplastic",
    'website': "https://www.coplastique.com",

    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    'depends': ['web', 'stock'],

    'data': [
        'report/report_templates.xml',
        'report/stock_report_visa.xml',
    ],

    'assets': {
        'web.report_assets_common': [
            'coplastic_report/static/src/css/report.css',
        ],
    },
}
