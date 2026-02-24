# -*- coding: utf-8 -*-
{
    'name': "Coplastic - Rapprochement automatique des paiements",
    'summary': "Rapprochement automatique du compte de suspens lors de la validation d'un paiement",
    'description': """
        Lorsqu'un paiement est validé sur un journal configuré pour le rapprochement automatique,
        ce module crée automatiquement une écriture comptable pour solder le compte de suspens
        et débiter/créditer le compte réel de la banque ou de la caisse.
    """,
    'author': "Coplastic",
    'website': "https://www.coplastique.com",
    'category': 'Accounting',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
