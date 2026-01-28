# -*- coding: utf-8 -*-

import logging
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    _logger.warning("openai library not installed")

# Instructions par défaut pour l'assistant fonctionnel
FUNC_INSTRUCTIONS = """Tu es OdooBot, l'assistant virtuel intégré à Odoo ERP pour l'entreprise Coplastic.

Tu aides les utilisateurs à utiliser Odoo pour leurs tâches quotidiennes :
- Créer des devis et commandes
- Gérer les clients et fournisseurs
- Suivre le stock et l'inventaire
- Créer des factures
- Utiliser le CRM

RÈGLES IMPORTANTES :
1. Tu es OdooBot, ne mentionne JAMAIS que tu es ChatGPT ou une IA
2. Réponds TOUJOURS en français
3. Sois concis et pratique
4. Guide l'utilisateur étape par étape
5. Utilise la documentation Odoo fournie pour donner des réponses précises
6. Si tu ne sais pas, dis-le honnêtement

Tu as accès à la documentation officielle Odoo 17 pour fournir des réponses précises."""

# Instructions par défaut pour l'assistant technique
TECH_INSTRUCTIONS = """Tu es OdooBot Tech, l'assistant technique intégré à Odoo ERP pour les développeurs de Coplastic.

Tu aides les développeurs à :
- Développer des modules Odoo personnalisés
- Comprendre l'ORM Odoo (models, fields, api)
- Créer des vues XML (form, tree, kanban, search)
- Développer en JavaScript/OWL pour le frontend
- Gérer la sécurité (access rights, record rules)
- Écrire des rapports QWeb
- Débugger et optimiser le code

RÈGLES IMPORTANTES :
1. Tu es OdooBot Tech, ne mentionne JAMAIS que tu es ChatGPT ou une IA
2. Réponds TOUJOURS en français
3. Fournis des exemples de code quand c'est pertinent
4. Explique les concepts techniques clairement
5. Utilise la documentation technique Odoo 17 fournie
6. Si tu ne sais pas, dis-le honnêtement

Tu as accès à la documentation technique officielle Odoo 17 (ORM, Views, JavaScript, etc.)."""


class CoplasticAssistant(models.Model):
    _name = 'cosplastic.assistant'
    _description = 'Assistant OpenAI pour CoplasticBot'
    _rec_name = 'name'

    name = fields.Char(string="Nom", default="CoplasticBot Assistant", required=True)
    assistant_type = fields.Selection([
        ('functional', 'Fonctionnel (Utilisateurs)'),
        ('technical', 'Technique (Développeurs)'),
    ], string="Type d'assistant", default='functional', required=True)
    assistant_id = fields.Char(string="Assistant ID (OpenAI)", readonly=True)
    vector_store_id = fields.Char(string="Vector Store ID (OpenAI)", readonly=True)
    file_ids_json = fields.Char(string="File IDs", readonly=True, default="[]")
    model = fields.Selection([
        ('gpt-4o-mini', 'GPT-4o Mini (Rapide, économique)'),
        ('gpt-4o', 'GPT-4o (Performant)'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
    ], string="Modèle", default='gpt-4o-mini', required=True)

    instructions = fields.Text(
        string="Instructions système",
        compute='_compute_default_instructions',
        store=True,
        readonly=False
    )

    @api.depends('assistant_type')
    def _compute_default_instructions(self):
        for record in self:
            if not record.instructions:
                if record.assistant_type == 'technical':
                    record.instructions = TECH_INSTRUCTIONS
                else:
                    record.instructions = FUNC_INSTRUCTIONS

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('configured', 'Configuré'),
        ('error', 'Erreur'),
    ], string="État", default='draft', readonly=True)

    files_count = fields.Integer(string="Fichiers uploadés", default=0, readonly=True)
    last_sync = fields.Datetime(string="Dernière synchronisation", readonly=True)
    error_message = fields.Text(string="Message d'erreur", readonly=True)

    def _get_openai_client(self):
        """Retourne le client OpenAI configuré"""
        if not OpenAI:
            raise UserError(_("La bibliothèque OpenAI n'est pas installée"))

        api_key = self.env['ir.config_parameter'].sudo().get_param('cosplastic_bot.openai_api_key')
        if not api_key:
            raise UserError(_("Clé API OpenAI non configurée. Allez dans Paramètres → Paramètres généraux."))

        return OpenAI(api_key=api_key)

    def action_create_assistant(self):
        """Crée l'Assistant OpenAI (sans Vector Store pour l'instant)"""
        self.ensure_one()

        try:
            client = self._get_openai_client()

            # Créer ou mettre à jour l'Assistant (sans file_search pour l'instant)
            assistant_params = {
                "name": self.name,
                "instructions": self.instructions,
                "model": self.model,
            }

            if self.assistant_id:
                # Mettre à jour l'assistant existant
                assistant = client.beta.assistants.update(
                    self.assistant_id,
                    **assistant_params
                )
                _logger.info(f"Assistant mis à jour: {assistant.id}")
            else:
                # Créer un nouvel assistant
                assistant = client.beta.assistants.create(**assistant_params)
                self.assistant_id = assistant.id
                _logger.info(f"Assistant créé: {assistant.id}")

            self.state = 'configured'
            self.error_message = False

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _('Assistant OpenAI configuré! Vous pouvez maintenant uploader la documentation.'),
                    'type': 'success',
                }
            }

        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.error(f"Erreur création Assistant: {e}")
            raise UserError(_(f"Erreur lors de la création de l'Assistant: {e}"))

    def action_upload_documentation(self):
        """Upload la documentation Odoo vers OpenAI selon le type d'assistant"""
        self.ensure_one()
        import os

        if not self.assistant_id:
            raise UserError(_("Créez d'abord l'Assistant avant d'uploader la documentation."))

        files_to_upload = []

        if self.assistant_type == 'technical':
            # Documentation technique pour développeurs
            docs_path = "/mnt/extra-addons/docs/odoo17_tech_docs"
            if not os.path.exists(docs_path):
                docs_path = "/root/co-plastic/odoo17/docs/odoo17_tech_docs"

            if not os.path.exists(docs_path):
                raise UserError(_("Dossier de documentation technique non trouvé."))

            # Backend: ORM, views, actions, security, data
            tech_backend = os.path.join(docs_path, 'reference', 'backend')
            if os.path.exists(tech_backend):
                priority_files = ['orm.txt', 'views.txt', 'actions.txt', 'security.txt', 'data.txt',
                                  'module.txt', 'http.txt', 'reports.txt', 'mixins.txt']
                for filename in priority_files:
                    filepath = os.path.join(tech_backend, filename)
                    if os.path.exists(filepath):
                        files_to_upload.append(filepath)

            # Frontend: JavaScript, OWL, services
            tech_frontend = os.path.join(docs_path, 'reference', 'frontend')
            if os.path.exists(tech_frontend):
                priority_files = ['javascript_reference.txt', 'owl_components.txt', 'services.txt',
                                  'hooks.txt', 'registries.txt', 'qweb.txt']
                for filename in priority_files:
                    filepath = os.path.join(tech_frontend, filename)
                    if os.path.exists(filepath):
                        files_to_upload.append(filepath)

            # Tutorials
            tutorials_path = os.path.join(docs_path, 'tutorials')
            if os.path.exists(tutorials_path):
                for filename in sorted(os.listdir(tutorials_path))[:5]:
                    if filename.endswith('.txt'):
                        files_to_upload.append(os.path.join(tutorials_path, filename))
        else:
            # Documentation fonctionnelle pour utilisateurs
            docs_path = "/mnt/extra-addons/docs/odoo17_docs"
            if not os.path.exists(docs_path):
                docs_path = "/root/co-plastic/odoo17/docs/odoo17_docs"

            if not os.path.exists(docs_path):
                raise UserError(_("Dossier de documentation fonctionnelle non trouvé."))

            important_dirs = ['sales', 'inventory', 'accounting', 'crm', 'purchase']
            for dir_name in important_dirs:
                dir_path = os.path.join(docs_path, dir_name)
                if os.path.exists(dir_path):
                    for filename in sorted(os.listdir(dir_path))[:4]:
                        if filename.endswith('.txt'):
                            files_to_upload.append(os.path.join(dir_path, filename))

        try:
            client = self._get_openai_client()
            uploaded_file_ids = []

            # Uploader les fichiers (max 20)
            for filepath in files_to_upload[:20]:
                with open(filepath, 'rb') as f:
                    file = client.files.create(
                        file=f,
                        purpose='assistants'
                    )
                    uploaded_file_ids.append(file.id)
                    _logger.info(f"Fichier uploadé: {os.path.basename(filepath)}")

            # Sauvegarder les IDs
            self.file_ids_json = json.dumps(uploaded_file_ids)
            self.files_count = len(uploaded_file_ids)
            self.last_sync = fields.Datetime.now()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _(f'{len(uploaded_file_ids)} fichiers de documentation uploadés!'),
                    'type': 'success',
                }
            }

        except Exception as e:
            self.error_message = str(e)
            _logger.error(f"Erreur upload documentation: {e}")
            raise UserError(_(f"Erreur lors de l'upload: {e}"))

    def get_response(self, question, user_id=None):
        """Obtient une réponse de l'Assistant pour une question"""
        self.ensure_one()

        if not self.assistant_id:
            return None

        try:
            client = self._get_openai_client()

            # Récupérer les file_ids uploadés
            file_ids = json.loads(self.file_ids_json) if self.file_ids_json else []

            # Créer un thread avec les fichiers si disponibles
            thread = client.beta.threads.create()

            # Construire le message avec attachements si on a des fichiers
            message_params = {
                "thread_id": thread.id,
                "role": "user",
                "content": question
            }

            if file_ids:
                message_params["attachments"] = [
                    {"file_id": fid, "tools": [{"type": "file_search"}]}
                    for fid in file_ids[:10]  # Max 10 attachements
                ]

            try:
                client.beta.threads.messages.create(**message_params)
            except Exception as e:
                # Fallback sans attachements
                _logger.warning(f"Erreur avec attachements, fallback: {e}")
                client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=question
                )

            # Exécuter l'assistant
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
            )

            if run.status == 'completed':
                # Récupérer les messages
                messages = client.beta.threads.messages.list(thread_id=thread.id)

                # Prendre la dernière réponse de l'assistant
                for msg in messages.data:
                    if msg.role == "assistant":
                        # Extraire le texte
                        for content in msg.content:
                            if hasattr(content, 'text'):
                                response_text = content.text.value
                                response_text = self._clean_citations(response_text)
                                return response_text

            _logger.warning(f"Run status: {run.status}")
            return None

        except Exception as e:
            _logger.error(f"Erreur Assistant response: {e}")
            return None

    def _clean_citations(self, text):
        """Nettoie les citations du texte de réponse"""
        import re
        # Supprimer les annotations de type 【4:0†source】
        text = re.sub(r'【\d+:\d+†[^】]*】', '', text)
        return text.strip()

    @api.model
    def get_active_assistant(self, assistant_type='functional'):
        """Retourne l'assistant actif configuré du type demandé"""
        assistant = self.search([
            ('state', '=', 'configured'),
            ('assistant_type', '=', assistant_type)
        ], limit=1)
        return assistant if assistant else None
