# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    coplastic_openai_api_key = fields.Char(
        string="Clé API OpenAI",
        help="Entrez votre clé API OpenAI (commence par sk-...)",
        config_parameter="cosplastic_bot.openai_api_key"
    )

    coplastic_chatgpt_model = fields.Selection([
        ('gpt-4o', 'GPT-4o'),
        ('gpt-4o-mini', 'GPT-4o Mini (Recommandé)'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
    ], string='Modèle ChatGPT',
        default='gpt-4o-mini',
        config_parameter="cosplastic_bot.chatgpt_model"
    )

    coplastic_max_tokens = fields.Integer(
        string="Max Tokens",
        default=1000,
        help="Nombre maximum de tokens dans la réponse",
        config_parameter="cosplastic_bot.max_tokens"
    )

    coplastic_temperature = fields.Float(
        string="Température",
        default=0.7,
        help="0 = déterministe, 1 = créatif",
        config_parameter="cosplastic_bot.temperature"
    )
