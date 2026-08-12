# -*- coding: utf-8 -*-
{
    "name": "Coplastic - Résumé Valorisation de Stock (XLSX)",
    "summary": "Export Excel de la valorisation de stock résumée : une ligne par produit (quantité finale + valeur), sans le détail des entrées/sorties.",
    "author": "Coplastic",
    "website": "https://www.coplastique.com",
    "category": "Inventory",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["stock", "report_xlsx"],
    "data": [
        "security/ir.model.access.csv",
        "report/report_actions.xml",
        "wizard/stock_valuation_summary_views.xml",
    ],
    "installable": True,
    "application": False,
}
