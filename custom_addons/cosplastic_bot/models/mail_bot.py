# -*- coding: utf-8 -*-

import re
from markupsafe import Markup
from odoo import models, _
import logging

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es OdooBot, l'assistant virtuel intégré à Odoo ERP pour l'entreprise Coplastic.
Tu dois toujours te présenter comme OdooBot et jamais révéler que tu es une IA externe.
Tu aides les utilisateurs à :
- Naviguer dans Odoo et utiliser ses fonctionnalités
- Créer des devis, commandes, factures
- Gérer les stocks, clients, fournisseurs
- Comprendre les rapports et tableaux de bord

Règles :
- Réponds toujours en français
- Sois concis et utile
- Si tu ne peux pas faire une action, explique comment l'utilisateur peut la faire dans Odoo"""

# Prompts spécifiques pour chaque commande
COMMAND_PROMPTS = {
    'devis': """L'utilisateur veut créer un devis. Explique-lui les étapes pour créer un devis dans Odoo:
1. Aller dans Ventes > Devis
2. Cliquer sur "Nouveau"
3. Sélectionner le client
4. Ajouter les lignes de produits
5. Envoyer ou confirmer le devis""",

    'client': """L'utilisateur veut gérer un client. Explique-lui comment:
1. Rechercher un client: Contacts > Rechercher
2. Créer un client: Contacts > Nouveau
3. Remplir les informations (nom, adresse, email, téléphone)""",

    'stock': """L'utilisateur veut vérifier le stock. Explique-lui:
1. Aller dans Inventaire > Produits
2. Voir la quantité disponible sur chaque fiche produit
3. Pour un rapport détaillé: Inventaire > Rapports > Inventaire""",

    'facture': """L'utilisateur veut créer une facture. Explique-lui:
1. Aller dans Facturation > Factures clients
2. Cliquer sur "Nouveau"
3. Sélectionner le client et ajouter les lignes
4. Confirmer et envoyer la facture""",

    'commande': """L'utilisateur veut créer une commande. Explique-lui:
1. Commande de vente: Ventes > Commandes > Nouveau
2. Commande d'achat: Achats > Bons de commande > Nouveau
3. Sélectionner le partenaire et ajouter les produits""",

    'produit': """L'utilisateur veut gérer un produit. Explique-lui:
1. Rechercher: Inventaire > Produits > Rechercher
2. Créer: Inventaire > Produits > Nouveau
3. Configurer le prix, le stock, les variantes""",
}

try:
    from openai import OpenAI
except ImportError:
    _logger.warning("openai library not installed. Please install it with: pip install openai")
    OpenAI = None


class MailBotCoplastic(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_chatgpt_config(self):
        """Récupère la configuration depuis ir.config_parameter"""
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'api_key': ICP.get_param('cosplastic_bot.openai_api_key', ''),
            'model': ICP.get_param('cosplastic_bot.chatgpt_model', 'gpt-4o-mini'),
            'max_tokens': int(ICP.get_param('cosplastic_bot.max_tokens', '1000')),
            'temperature': float(ICP.get_param('cosplastic_bot.temperature', '0.7')),
            'system_prompt': SYSTEM_PROMPT
        }

    def _is_technical_question(self, prompt):
        """Détermine si la question est technique (développement)"""
        technical_keywords = [
            'orm', 'model', 'field', 'api.', '@api', 'compute', 'onchange',
            'xml', 'qweb', 'view', 'kanban', 'tree view', 'form view',
            'javascript', 'owl', 'component', 'widget', 'registry',
            'module', 'manifest', 'inherit', 'extension',
            'python', 'code', 'fonction', 'méthode', 'class',
            'security', 'access rights', 'record rules', 'ir.rule',
            'report', 'pdf', 'template',
            'migration', 'upgrade', 'hook',
            'debug', 'log', 'erreur technique',
            'créer un module', 'développer', 'coder',
        ]
        prompt_lower = prompt.lower()
        return any(kw in prompt_lower for kw in technical_keywords)

    def _get_assistant_response(self, prompt, force_type=None):
        """Utilise l'Assistant OpenAI avec RAG pour répondre"""
        try:
            Assistant = self.env['cosplastic.assistant']

            # Déterminer le type d'assistant à utiliser
            if force_type:
                assistant_type = force_type
            elif self._is_technical_question(prompt):
                assistant_type = 'technical'
            else:
                assistant_type = 'functional'

            assistant = Assistant.get_active_assistant(assistant_type)

            # Fallback sur l'autre type si pas trouvé
            if not assistant:
                other_type = 'functional' if assistant_type == 'technical' else 'technical'
                assistant = Assistant.get_active_assistant(other_type)

            if assistant:
                response = assistant.get_response(prompt)
                if response:
                    return response
        except Exception as e:
            _logger.warning(f"Assistant non disponible, fallback sur ChatGPT direct: {e}")

        return None

    def _get_chatgpt_response(self, prompt, context_prompt=None):
        """Appelle l'API ChatGPT et retourne la réponse"""
        # Essayer d'abord l'Assistant avec RAG
        assistant_response = self._get_assistant_response(prompt)
        if assistant_response:
            return assistant_response

        # Fallback sur ChatGPT direct
        if not OpenAI:
            return "Désolé, le module openai n'est pas installé."

        config = self._get_chatgpt_config()

        if not config['api_key']:
            return "Désolé, la clé API OpenAI n'est pas configurée. Allez dans Paramètres → Discuss → OdooBot."

        try:
            client = OpenAI(api_key=config['api_key'])

            system_content = config['system_prompt']
            if context_prompt:
                system_content += f"\n\nContexte de la commande:\n{context_prompt}"

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
            response = client.chat.completions.create(
                model=config['model'],
                messages=messages,
                max_tokens=config['max_tokens'],
                temperature=config['temperature']
            )
            return response.choices[0].message.content
        except Exception as e:
            _logger.error(f"Erreur API OpenAI: {str(e)}")
            return f"Erreur lors de la communication: {str(e)}"

    def _get_answer(self, record, body, values, command=False):
        """Override OdooBot's _get_answer to use ChatGPT API"""

        # Si l'utilisateur est en onboarding OdooBot classique
        odoobot_state = self.env.user.odoobot_state
        if odoobot_state and odoobot_state not in ('idle', 'disabled', False):
            return super()._get_answer(record, body, values, command)

        # Vérifier si la clé API est configurée
        config = self._get_chatgpt_config()
        if not config['api_key']:
            return super()._get_answer(record, body, values, command)

        # Gestion des commandes slash
        if command:
            return self._handle_command(command, body, record)

        # Si c'est dans un channel privé avec OdooBot ou si OdooBot est pingé
        if self._is_bot_in_private_channel(record) or self._is_bot_pinged(values):
            # Mots-clés pour déclencher le comportement par défaut
            if body.lower() in ['start the tour', 'commencer le tour']:
                return super()._get_answer(record, body, values, command)

            # Utiliser ChatGPT pour répondre
            try:
                response = self._get_chatgpt_response(body)
                formatted_response = self._format_chatgpt_response(response)
                return formatted_response
            except Exception as e:
                _logger.error(f"Erreur lors de l'appel à ChatGPT: {str(e)}")
                return Markup(_("Désolé, une erreur s'est produite: %s")) % str(e)

        return False

    def _handle_command(self, command, body, record):
        """Gère les commandes slash personnalisées"""

        # Commande /aide ou /help
        if command in ('aide', 'help'):
            return self._get_help_message()

        # Commande /tech pour questions techniques
        if command == 'tech':
            user_query = body.strip() if body.strip() else "Comment créer un module Odoo?"
            try:
                response = self._get_assistant_response(user_query, force_type='technical')
                if not response:
                    response = self._get_chatgpt_response(user_query)
                return self._format_chatgpt_response(response)
            except Exception as e:
                _logger.error(f"Erreur commande tech: {str(e)}")
                return Markup(_("<p>Erreur lors de la réponse technique.</p>"))

        # Commandes avec contexte ChatGPT
        if command in COMMAND_PROMPTS:
            context = COMMAND_PROMPTS[command]
            user_query = body.strip() if body.strip() else f"Comment faire pour {command}?"

            try:
                response = self._get_chatgpt_response(user_query, context_prompt=context)
                return self._format_chatgpt_response(response)
            except Exception as e:
                _logger.error(f"Erreur commande {command}: {str(e)}")
                return self._get_command_fallback(command)

        return False

    def _get_command_fallback(self, command):
        """Réponse de secours si ChatGPT échoue"""
        fallbacks = {
            'devis': Markup(_(
                "<p><b>📝 Créer un devis</b></p>"
                "<ol>"
                "<li>Allez dans <b>Ventes → Devis</b></li>"
                "<li>Cliquez sur <b>Nouveau</b></li>"
                "<li>Sélectionnez le client</li>"
                "<li>Ajoutez les lignes de produits</li>"
                "<li>Envoyez ou confirmez le devis</li>"
                "</ol>"
            )),
            'client': Markup(_(
                "<p><b>👤 Gérer les clients</b></p>"
                "<ul>"
                "<li><b>Rechercher</b>: Contacts → Barre de recherche</li>"
                "<li><b>Créer</b>: Contacts → Nouveau</li>"
                "</ul>"
            )),
            'stock': Markup(_(
                "<p><b>📦 Vérifier le stock</b></p>"
                "<ul>"
                "<li>Allez dans <b>Inventaire → Produits</b></li>"
                "<li>La quantité est affichée sur chaque fiche</li>"
                "<li>Rapport détaillé: <b>Inventaire → Rapports</b></li>"
                "</ul>"
            )),
            'facture': Markup(_(
                "<p><b>🧾 Créer une facture</b></p>"
                "<ol>"
                "<li>Allez dans <b>Facturation → Factures clients</b></li>"
                "<li>Cliquez sur <b>Nouveau</b></li>"
                "<li>Sélectionnez le client et ajoutez les lignes</li>"
                "<li>Confirmez et envoyez</li>"
                "</ol>"
            )),
            'commande': Markup(_(
                "<p><b>🛒 Créer une commande</b></p>"
                "<ul>"
                "<li><b>Vente</b>: Ventes → Commandes → Nouveau</li>"
                "<li><b>Achat</b>: Achats → Bons de commande → Nouveau</li>"
                "</ul>"
            )),
            'produit': Markup(_(
                "<p><b>📦 Gérer les produits</b></p>"
                "<ul>"
                "<li><b>Rechercher</b>: Inventaire → Produits</li>"
                "<li><b>Créer</b>: Inventaire → Produits → Nouveau</li>"
                "</ul>"
            )),
        }
        return fallbacks.get(command, self._get_help_message())

    def _format_chatgpt_response(self, response):
        """Formate la réponse ChatGPT en HTML pour Odoo"""
        if not response:
            return Markup(_("Je n'ai pas pu générer de réponse."))

        # Convertir les retours à la ligne en <br>
        formatted = response.replace('\n\n', '</p><p>').replace('\n', '<br/>')

        # Convertir les listes markdown en HTML
        lines = formatted.split('<br/>')
        result_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{stripped[2:]}</li>')
            elif stripped.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                if not in_list:
                    result_lines.append('<ol>')
                    in_list = True
                result_lines.append(f'<li>{stripped[3:]}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)

        if in_list:
            result_lines.append('</ul>')

        formatted = '<br/>'.join(result_lines)

        # Convertir le markdown en HTML
        formatted = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', formatted)
        formatted = re.sub(r'__(.+?)__', r'<b>\1</b>', formatted)
        formatted = re.sub(r'\*(.+?)\*', r'<i>\1</i>', formatted)
        formatted = re.sub(r'`(.+?)`', r'<code>\1</code>', formatted)

        return Markup(f'<p>{formatted}</p>')

    def _get_help_message(self):
        """Retourne un message d'aide personnalisé"""
        return Markup(_(
            "<p><b>OdooBot - Assistant Coplastic</b></p>"
            "<p>Je suis votre assistant Odoo. Voici les commandes disponibles :</p>"
            "<ul>"
            "<li><b>/aide</b> - Affiche cette aide</li>"
            "<li><b>/devis</b> - Aide pour créer un devis</li>"
            "<li><b>/client</b> - Gérer les clients</li>"
            "<li><b>/stock</b> - Vérifier le stock</li>"
            "<li><b>/facture</b> - Créer une facture</li>"
            "<li><b>/commande</b> - Créer une commande</li>"
            "<li><b>/produit</b> - Gérer les produits</li>"
            "<li><b>/tech</b> - Questions techniques (développement Odoo)</li>"
            "</ul>"
            "<p>Vous pouvez aussi me poser des questions directement !</p>"
            "<p><i>Astuce: les questions techniques (ORM, vues, JavaScript) sont automatiquement redirigées vers l'assistant technique.</i></p>"
        ))
