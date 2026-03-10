# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    openai = None


class BotChat(models.Model):
    _name = 'cosplastic.bot.chat'
    _description = 'Conversation Bot IA'
    _order = 'create_date desc'
    _rec_name = 'title'

    title = fields.Char(string='Titre', compute='_compute_title', store=True)
    user_id = fields.Many2one('res.users', string='Utilisateur',
                               default=lambda self: self.env.user, required=True)
    config_id = fields.Many2one('cosplastic.bot.config', string='Configuration',
                                 domain=[('active', '=', True)])

    message_ids = fields.One2many('cosplastic.bot.message', 'chat_id', string='Messages')

    state = fields.Selection([
        ('active', 'Active'),
        ('closed', 'Fermée'),
    ], string='État', default='active')

    # Champ pour nouvelle question
    new_message = fields.Text(string='Nouveau message')

    @api.depends('message_ids')
    def _compute_title(self):
        for record in self:
            first_msg = record.message_ids.filtered(lambda m: m.role == 'user')[:1]
            if first_msg:
                record.title = first_msg.content[:50] + '...' if len(first_msg.content) > 50 else first_msg.content
            else:
                record.title = f"Conversation #{record.id or 'Nouvelle'}"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Récupérer la config active par défaut
        config = self.env['cosplastic.bot.config'].search([('active', '=', True)], limit=1)
        if config:
            res['config_id'] = config.id
        return res

    def send_message(self):
        """Envoie un message au bot et récupère la réponse"""
        self.ensure_one()

        if not self.new_message:
            raise UserError("Veuillez saisir un message.")

        if not self.config_id:
            raise UserError("Veuillez configurer une connexion API.")

        if not openai:
            raise UserError("La bibliothèque openai n'est pas installée.")

        # Créer le message utilisateur
        self.env['cosplastic.bot.message'].create({
            'chat_id': self.id,
            'role': 'user',
            'content': self.new_message,
        })

        # Préparer les messages pour l'API
        messages = [{'role': 'system', 'content': self.config_id.system_prompt}]

        for msg in self.message_ids.sorted('create_date'):
            messages.append({
                'role': msg.role,
                'content': msg.content
            })

        try:
            client = openai.OpenAI(api_key=self.config_id.api_key)
            response = client.chat.completions.create(
                model=self.config_id.model,
                messages=messages,
                max_tokens=self.config_id.max_tokens,
                temperature=self.config_id.temperature
            )

            assistant_message = response.choices[0].message.content

            # Créer la réponse du bot
            self.env['cosplastic.bot.message'].create({
                'chat_id': self.id,
                'role': 'assistant',
                'content': assistant_message,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
            })

            # Vider le champ de saisie
            self.new_message = False

            # Parser et exécuter les actions si présentes
            self._execute_actions(assistant_message)

        except Exception as e:
            _logger.error(f"Erreur API OpenAI: {str(e)}")
            raise UserError(f"Erreur lors de la communication avec l'IA: {str(e)}")

        return True

    def _execute_actions(self, response):
        """Parse la réponse et exécute les actions Odoo si détectées"""
        # TODO: Implémenter la logique d'exécution des actions
        # Exemple: détecter des commandes comme [ACTION:create_quotation:...]
        pass

    def action_close(self):
        """Ferme la conversation"""
        self.write({'state': 'closed'})

    def action_reopen(self):
        """Réouvre la conversation"""
        self.write({'state': 'active'})


class BotMessage(models.Model):
    _name = 'cosplastic.bot.message'
    _description = 'Message Bot'
    _order = 'create_date asc'

    chat_id = fields.Many2one('cosplastic.bot.chat', string='Conversation',
                               required=True, ondelete='cascade')
    role = fields.Selection([
        ('user', 'Utilisateur'),
        ('assistant', 'Assistant'),
        ('system', 'Système'),
    ], string='Rôle', required=True)

    content = fields.Text(string='Contenu', required=True)
    tokens_used = fields.Integer(string='Tokens utilisés')

    # Pour tracer les actions exécutées
    action_executed = fields.Boolean(string='Action exécutée', default=False)
    action_result = fields.Text(string='Résultat de l\'action')
