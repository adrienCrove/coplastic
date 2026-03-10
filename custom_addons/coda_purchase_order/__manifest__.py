{
    'name': 'Coda Purchase Order - Rapports Achats',
    'version': '17.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Rapports personnalisés pour les achats (Demande de Prix et Bon de Commande Fournisseur)',
    'author': 'Coplastic',
    'depends': ['purchase'],
    'data': [
        'reports/report_coda_demande_prix.xml',
        'reports/report_coda_bon_commande_achat.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
