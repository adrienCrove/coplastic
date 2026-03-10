# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    _logger.warning("openai library not installed. Please install it with: pip install openai")
    openai = None


class CoplasticBotConfig(models.Model):
    _name = 'cosplastic.bot.config'
    _description = 'Configuration CoplasticBot (ChatGPT)'
    _rec_name = 'name'

    name = fields.Char(string='Nom', required=True, default='Configuration ChatGPT')
    api_key = fields.Char(string='Clé API OpenAI', required=True)
    model = fields.Selection([
        ('gpt-4o', 'GPT-4o'),
        ('gpt-4o-mini', 'GPT-4o Mini (Recommandé)'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
    ], string='Modèle', default='gpt-4o-mini', required=True)

    max_tokens = fields.Integer(string='Max Tokens', default=1000)
    temperature = fields.Float(string='Température', default=0.7,
                               help='0 = réponses déterministes, 1 = réponses créatives')

    system_prompt = fields.Text(
        string='Prompt Système',
        default="""Tu es OdooBot amélioré par l'IA pour l'entreprise Coplastic.
Tu aides les utilisateurs à utiliser Odoo ERP.
Tu peux les aider à :
- Comprendre comment utiliser les différents modules d'Odoo
- Créer des devis, commandes, factures
- Gérer les stocks et inventaires
- Gérer les clients et fournisseurs
- Analyser les données de vente

Réponds toujours en français, de manière concise et utile.
Si on te demande d'effectuer une action que tu ne peux pas faire, explique comment l'utilisateur peut le faire lui-même dans Odoo."""
    )

    active = fields.Boolean(string='Actif', default=True)
    company_id = fields.Many2one('res.company', string='Société',
                                  default=lambda self: self.env.company)

    @api.model
    def get_active_config(self):
        """Récupère la configuration active"""
        config = self.search([('active', '=', True)], limit=1)
        return config

    def test_connection(self):
        """Teste la connexion à l'API OpenAI"""
        self.ensure_one()
        if not openai:
            raise UserError("La bibliothèque openai n'est pas installée. Installez-la avec: pip install openai")

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test de connexion. Réponds juste 'OK'."}],
                max_tokens=10
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connexion réussie',
                    'message': f"Réponse: {response.choices[0].message.content}",
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(f"Erreur de connexion: {str(e)}")

    def get_chatgpt_response(self, user_message):
        """Appelle l'API ChatGPT et retourne la réponse"""
        self.ensure_one()
        if not openai:
            return "Désolé, le module ChatGPT n'est pas configuré correctement (openai non installé)."

        if not self.api_key or self.api_key == 'YOUR_API_KEY_HERE':
            return "Désolé, la clé API OpenAI n'est pas configurée. Contactez votre administrateur."

        try:
            client = openai.OpenAI(api_key=self.api_key)

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            return response.choices[0].message.content

        except Exception as e:
            _logger.error(f"Erreur API OpenAI: {str(e)}")
            return f"Désolé, une erreur s'est produite lors de la communication avec l'IA: {str(e)}"
