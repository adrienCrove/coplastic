# -*- coding: utf-8 -*-
{
    'name': 'Coplastic - Journaux vides par défaut (rapports)',
    'version': '17.0.1.0.0',
    'summary': "Ne pré-sélectionne plus tous les journaux dans les wizards d'impression de rapports",
    'description': """
Dans base_accounting_kit, les assistants d'impression (Grand livre, Balance,
Journaux, Grand livre partenaire, Balance âgée, Livre de caisse/banque/journalier,
Rapport de TVA, Flux de trésorerie) pré-cochent TOUS les journaux.

Ce module inverse le comportement : le champ « Journaux » démarre VIDE, pour que
l'utilisateur choisisse lui-même le(s) journal(aux) voulu(s), au lieu de devoir
décocher tout le reste.

Non-intrusif : override par héritage, base_accounting_kit n'est pas modifié.
""",
    'category': 'Accounting/Accounting',
    'author': 'Coplastic',
    'license': 'LGPL-3',
    'depends': ['base_accounting_kit'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
