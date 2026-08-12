# -*- coding: utf-8 -*-
{
    'name': "FNE - Point de Vente (Côte d'Ivoire)",
    'summary': "Certification FNE des tickets de caisse et impression du reçu normalisé",
    'description': """
FNE au Point de Vente
=====================
Passerelle entre la certification FNE/DGI et le Point de Vente Odoo.

Un ticket de caisse n'est pas une facture : il ne produit aucun account.move
tant qu'il n'est pas facturé. Ce module lui apporte son propre circuit de
certification, à la demande du caissier.

Fonctionnalités :
- Bouton « Certifier / Imprimer FNE » dans l'écran Commandes du POS
- Bloc FNE (référence, QR Code, logo) ajouté au ticket 80mm
- Report PDF A4 au format normalisé DGI, depuis le backend
- Mode de paiement FNE configurable par mode de paiement POS
- Certification manuelle de rattrapage depuis Point de Vente → Commandes
    """,
    'author': "Coplastic",
    'website': "https://coplastic.adriennde.com",
    'category': 'Accounting/Localizations',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['l10n_ci_fne', 'point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_order_views.xml',
        'report/fne_pos_receipt_report.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_ci_fne_pos/static/src/js/**/*',
            'l10n_ci_fne_pos/static/src/xml/**/*',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': True,
}
