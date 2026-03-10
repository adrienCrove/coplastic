{
    'name': 'Coplastic Dépôt-Vente',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Gestion des ventes en dépôt-vente avec vendeurs indépendants',
    'description': """
        Module de gestion du dépôt-vente :
        - Remise de produits à des vendeurs indépendants
        - Suivi du stock par vendeur (emplacement dédié)
        - Enregistrement des retours d'invendus
        - Génération automatique de la facture client pour les vendus
    """,
    'author': 'Coplastic',
    'depends': ['stock', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/stock_location_data.xml',
        'views/depot_vente_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
