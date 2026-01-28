# -*- coding: utf-8 -*-
{
    'name': 'Co-Plastic Theme',
    'version': '17.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': 'Thème personnalisé aux couleurs de Co-Plastic',
    'description': """
        Ce module personnalise les couleurs du thème Odoo
        pour correspondre à l'identité visuelle de Co-Plastic.

        Couleurs principales:
        - Vert Co-Plastic: #1B7B3D
        - Gris secondaire: #6c757d
        - Blanc: #ffffff
    """,
    'author': 'Co-Plastic',
    'website': 'https://coplastique.com',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'cosplastic_theme/static/src/scss/primary_variables.scss',
        ],
        'web.assets_frontend': [
            'cosplastic_theme/static/src/scss/primary_variables.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
