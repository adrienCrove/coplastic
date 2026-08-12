# -*- coding: utf-8 -*-
"""Vide la sélection des journaux par défaut dans les assistants d'impression
de base_accounting_kit, pour laisser l'utilisateur choisir lui-même.

base_accounting_kit ajoute au modèle partagé ``account.report`` :
  - un champ ``journal_ids`` avec ``default=`` tous les journaux ;
  - un ``@api.onchange('company_id')`` qui recharge tous les journaux à
    l'ouverture du formulaire.
Tous les assistants (Grand livre, Balance, Journaux, Grand livre partenaire,
Balance âgée, Livres caisse/banque/journalier...) héritent de ce modèle.

On surcharge ici ce modèle partagé (module chargé APRÈS base_accounting_kit,
donc override déterministe) pour démarrer la sélection VIDE.
"""
from odoo import api, models


class AccountReportJournalDefault(models.Model):
    _inherit = 'account.report'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Ne pas pré-remplir les journaux : l'utilisateur choisit lui-même
        res.pop('journal_ids', None)
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        # Neutralise le rechargement "tous les journaux" de base_accounting_kit
        self.journal_ids = [(5, 0, 0)]
