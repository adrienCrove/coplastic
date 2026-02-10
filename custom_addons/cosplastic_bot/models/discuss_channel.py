# -*- coding: utf-8 -*-

from odoo import api, models, _
from markupsafe import Markup


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    # ==========================================
    # COMMANDES SLASH COPLASTICBOT
    # ==========================================

    def _post_bot_message(self, command, body=""):
        """Poste un message d'OdooBot en réponse à une commande"""
        odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        mail_bot = self.env['mail.bot']

        # Récupérer la réponse du bot
        answer = mail_bot._handle_command(command, body, self)

        if answer:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
            self.with_context(mail_create_nosubscribe=True).sudo().message_post(
                body=answer,
                author_id=odoobot_id,
                message_type='comment',
                subtype_id=subtype_id
            )

    def execute_command_aide(self, **kwargs):
        """Commande /aide - Affiche l'aide de CoplasticBot"""
        body = kwargs.get('body', '')
        self._post_bot_message("aide", body)

    def execute_command_devis(self, **kwargs):
        """Commande /devis - Aide à créer un devis"""
        body = kwargs.get('body', '')
        self._post_bot_message("devis", body)

    def execute_command_client(self, **kwargs):
        """Commande /client - Recherche ou crée un client"""
        body = kwargs.get('body', '')
        self._post_bot_message("client", body)

    def execute_command_stock(self, **kwargs):
        """Commande /stock - Vérifie le stock d'un produit"""
        body = kwargs.get('body', '')
        self._post_bot_message("stock", body)

    def execute_command_facture(self, **kwargs):
        """Commande /facture - Aide à créer une facture"""
        body = kwargs.get('body', '')
        self._post_bot_message("facture", body)

    def execute_command_commande(self, **kwargs):
        """Commande /commande - Aide à créer une commande"""
        body = kwargs.get('body', '')
        self._post_bot_message("commande", body)

    def execute_command_produit(self, **kwargs):
        """Commande /produit - Recherche un produit"""
        body = kwargs.get('body', '')
        self._post_bot_message("produit", body)

    def execute_command_tech(self, **kwargs):
        """Commande /tech - Questions techniques développement Odoo"""
        body = kwargs.get('body', '')
        self._post_bot_message("tech", body)

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
            {
                'name': 'tech',
                'help': _("Questions techniques (développement Odoo)"),
            },
        ]

        commands.extend(coplastic_commands)
        return commands
