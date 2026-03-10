# -*- coding: utf-8 -*-

import logging
import json
import os
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    _logger.warning("openai library not installed")


class CoplasticAssistant(models.Model):
    _name = 'cosplastic.assistant'
    _description = 'Assistant OpenAI pour CoplasticBot'
    _rec_name = 'name'

    name = fields.Char(string="Nom", default="CoplasticBot Assistant", required=True)
    assistant_id = fields.Char(string="Assistant ID (OpenAI)", readonly=True)
    file_ids = fields.Text(string="File IDs (JSON)", readonly=True, default="[]")
    model = fields.Selection([
        ('gpt-4o-mini', 'GPT-4o Mini (Rapide, économique)'),
        ('gpt-4o', 'GPT-4o (Performant)'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
    ], string="Modèle", default='gpt-4o-mini', required=True)

    instructions = fields.Text(
        string="Instructions système",
        default="""Tu es OdooBot, l'assistant virtuel intégré à Odoo ERP pour l'entreprise Coplastic.

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
    )

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
        """Crée l'Assistant OpenAI"""
        self.ensure_one()

        try:
            client = self._get_openai_client()

            # Paramètres de l'assistant
            assistant_params = {
                "name": self.name,
                "instructions": self.instructions,
                "model": self.model,
                "tools": [{"type": "file_search"}],
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
                    'message': _('Assistant OpenAI configuré avec succès! Vous pouvez maintenant uploader la documentation.'),
                    'type': 'success',
                }
            }

        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.error(f"Erreur création Assistant: {e}")
            raise UserError(_(f"Erreur lors de la création de l'Assistant: {e}"))

    def action_upload_documentation(self):
        """Upload la documentation Odoo et crée un Vector Store"""
        self.ensure_one()

        if not self.assistant_id:
            raise UserError(_("Créez d'abord l'Assistant avant d'uploader la documentation."))

        docs_path = "/mnt/extra-addons/docs/odoo17_docs"

        # Vérifier si le dossier existe dans le container
        if not os.path.exists(docs_path):
            docs_path = "/root/co-plastic/odoo17/docs/odoo17_docs"

        if not os.path.exists(docs_path):
            raise UserError(_("Dossier de documentation non trouvé. Exécutez d'abord le script de téléchargement."))

        try:
            client = self._get_openai_client()
            uploaded_file_ids = []

            # Parcourir tous les fichiers .txt et les uploader
            for root, dirs, files in os.walk(docs_path):
                for filename in files:
                    if filename.endswith('.txt'):
                        filepath = os.path.join(root, filename)

                        # Upload le fichier
                        with open(filepath, 'rb') as f:
                            file = client.files.create(
                                file=f,
                                purpose='assistants'
                            )
                            uploaded_file_ids.append(file.id)
                            _logger.info(f"Fichier uploadé: {filename} -> {file.id}")

            # Créer un Vector Store avec tous les fichiers
            vector_store = client.beta.vector_stores.create(
                name=f"Odoo 17 Docs - {self.name}",
                file_ids=uploaded_file_ids
            )
            _logger.info(f"Vector Store créé: {vector_store.id}")

            # Mettre à jour l'assistant avec le Vector Store
            client.beta.assistants.update(
                self.assistant_id,
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store.id]
                    }
                }
            )

            self.file_ids = json.dumps(uploaded_file_ids)
            self.files_count = len(uploaded_file_ids)
            self.last_sync = fields.Datetime.now()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès'),
                    'message': _(f'{len(uploaded_file_ids)} fichiers uploadés et indexés!'),
                    'type': 'success',
                }
            }

        except AttributeError as e:
            # Si vector_stores n'est pas disponible, utiliser une approche alternative
            _logger.warning(f"Vector Stores non disponible, utilisation de l'approche alternative: {e}")
            return self._upload_docs_alternative(docs_path, client)

        except Exception as e:
            self.error_message = str(e)
            _logger.error(f"Erreur upload documentation: {e}")
            raise UserError(_(f"Erreur lors de l'upload: {e}"))

    def _upload_docs_alternative(self, docs_path, client):
        """Approche alternative sans Vector Stores - utilise les fichiers attachés au thread"""
        try:
            uploaded_file_ids = []

            # Uploader les fichiers les plus importants (limité à 20 pour éviter les limites)
            important_dirs = ['sales', 'inventory', 'accounting', 'crm', 'purchase']
            files_to_upload = []

            for dir_name in important_dirs:
                dir_path = os.path.join(docs_path, dir_name)
                if os.path.exists(dir_path):
                    for filename in os.listdir(dir_path)[:4]:  # 4 fichiers par catégorie
                        if filename.endswith('.txt'):
                            files_to_upload.append(os.path.join(dir_path, filename))

            for filepath in files_to_upload[:20]:  # Maximum 20 fichiers
                with open(filepath, 'rb') as f:
                    file = client.files.create(
                        file=f,
                        purpose='assistants'
                    )
                    uploaded_file_ids.append(file.id)
                    _logger.info(f"Fichier uploadé: {os.path.basename(filepath)} -> {file.id}")

            self.file_ids = json.dumps(uploaded_file_ids)
            self.files_count = len(uploaded_file_ids)
            self.last_sync = fields.Datetime.now()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Succès (mode simplifié)'),
                    'message': _(f'{len(uploaded_file_ids)} fichiers uploadés! Les fichiers seront utilisés lors des questions.'),
                    'type': 'success',
                }
            }

        except Exception as e:
            self.error_message = str(e)
            _logger.error(f"Erreur upload alternative: {e}")
            raise UserError(_(f"Erreur lors de l'upload alternatif: {e}"))

    def get_response(self, question, user_id=None):
        """Obtient une réponse de l'Assistant pour une question"""
        self.ensure_one()

        if not self.assistant_id:
            return None

        try:
            client = self._get_openai_client()

            # Récupérer les file_ids uploadés
            file_ids = json.loads(self.file_ids) if self.file_ids else []

            # Créer un thread avec les fichiers attachés si disponibles
            thread_params = {}
            if file_ids:
                thread_params['tool_resources'] = {
                    "file_search": {
                        "vector_stores": [{
                            "file_ids": file_ids[:20]  # Limite de 20 fichiers par vector store
                        }]
                    }
                }

            try:
                thread = client.beta.threads.create(**thread_params)
            except Exception:
                # Fallback: créer un thread simple
                thread = client.beta.threads.create()

            # Ajouter le message de l'utilisateur
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
                            if content.type == "text":
                                response_text = content.text.value
                                # Nettoyer les annotations de citation
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
    def get_active_assistant(self):
        """Retourne l'assistant actif configuré"""
        assistant = self.search([('state', '=', 'configured')], limit=1)
        return assistant if assistant else None
