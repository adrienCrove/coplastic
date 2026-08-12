# -*- coding: utf-8 -*-
{
    'name': 'Coplastic - Partenaires',
    'version': '17.0.1.0.0',
    'summary': 'Analyse de consommation mensuelle par client',
    'category': 'Sales',
    'author': 'Coplastic',
    'depends': ['sale', 'base'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_search_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
