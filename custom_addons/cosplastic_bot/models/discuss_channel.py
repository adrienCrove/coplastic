# -*- coding: utf-8 -*-

from odoo import api, models, _
from markupsafe import Markup


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    # ==========================================
    # COMMANDES SLASH COPLASTICBOT
    # ==========================================

    def execute_command_aide(self, **kwargs):
        """Commande /aide - Affiche l'aide de CoplasticBot"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="aide")

    def execute_command_devis(self, **kwargs):
        """Commande /devis - Aide à créer un devis"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="devis")

    def execute_command_client(self, **kwargs):
        """Commande /client - Recherche ou crée un client"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="client")

    def execute_command_stock(self, **kwargs):
        """Commande /stock - Vérifie le stock d'un produit"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="stock")

    def execute_command_facture(self, **kwargs):
        """Commande /facture - Aide à créer une facture"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="facture")

    def execute_command_commande(self, **kwargs):
        """Commande /commande - Aide à créer une commande"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="commande")

    def execute_command_produit(self, **kwargs):
        """Commande /produit - Recherche un produit"""
        self.env['mail.bot']._apply_logic(self, kwargs, command="produit")

    @api.model
    def _get_available_commands(self):
        """Ajoute les commandes CoplasticBot aux commandes disponibles"""
        commands = super()._get_available_commands()

        # Commandes CoplasticBot
        coplastic_commands = [
            {
                'name': 'aide',
                'help': _("Affiche l'aide de l'assistant"),
            },
            {
                'name': 'devis',
                'help': _("Aide à créer un nouveau devis"),
            },
            {
                'name': 'client',
                'help': _("Recherche ou crée un client"),
            },
            {
                'name': 'stock',
                'help': _("Vérifie le stock d'un produit"),
            },
            {
                'name': 'facture',
                'help': _("Aide à créer une facture"),
            },
            {
                'name': 'commande',
                'help': _("Aide à créer une commande"),
            },
            {
                'name': 'produit',
                'help': _("Recherche un produit"),
            },
        ]

        commands.extend(coplastic_commands)
        return commands
