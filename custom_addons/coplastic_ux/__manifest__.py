{
    'name': 'Coplastic UX',
    'version': '17.0.1.0.0',
    'category': 'Technical',
    'summary': 'Améliorations UX pour Coplastic (navigation Enter dans les listes)',
    'author': 'Coplastic',
    'depends': ['web', 'account', 'sales_team'],
    'assets': {
        'web.assets_backend': [
            'coplastic_ux/static/src/js/list_enter_navigation.js',
        ],
    },
    'data': [
        'data/menu_access.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
