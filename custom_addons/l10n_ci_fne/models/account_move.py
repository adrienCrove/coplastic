# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # === Champs FNE ===
    fne_reference = fields.Char(
        string="Référence FNE",
        readonly=True,
        copy=False,
        help="Numéro de facture normalisée attribué par la DGI"
    )
    fne_token = fields.Char(
        string="Token FNE",
        readonly=True,
        copy=False,
        help="URL de vérification FNE pour le QR Code"
    )
    fne_qr_code = fields.Binary(
        string="QR Code FNE",
        compute='_compute_fne_qr_code',
        store=True,
        copy=False,
        help="QR Code de vérification FNE"
    )
    fne_certified = fields.Boolean(
        string="Certifiée FNE",
        readonly=True,
        copy=False,
        default=False,
    )
    fne_invoice_id = fields.Char(
        string="ID Facture FNE",
        readonly=True,
        copy=False,
        help="Identifiant interne de la facture sur la plateforme FNE"
    )
    fne_ncc = fields.Char(
        string="NCC Entreprise",
        readonly=True,
        copy=False,
    )
    fne_balance_sticker = fields.Integer(
        string="Solde Stickers FNE",
        readonly=True,
        copy=False,
    )
    fne_certification_date = fields.Datetime(
        string="Date de certification",
        readonly=True,
        copy=False,
    )
    fne_error_message = fields.Text(
        string="Erreur FNE",
        readonly=True,
        copy=False,
    )

    @api.depends('fne_token')
    def _compute_fne_qr_code(self):
        """Génère le QR Code à partir du token FNE"""
        for move in self:
            if move.fne_token:
                try:
                    import qrcode
                    import io
                    import base64

                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=6,
                        border=2,
                    )
                    qr.add_data(move.fne_token)
                    qr.make(fit=True)

                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    move.fne_qr_code = base64.b64encode(buffer.getvalue())
                except ImportError:
                    _logger.warning("Module qrcode non installé. pip install qrcode[pil]")
                    move.fne_qr_code = False
                except Exception as e:
                    _logger.error("Erreur génération QR Code: %s", e)
                    move.fne_qr_code = False
            else:
                move.fne_qr_code = False

    def _post(self, soft=True):
        """Override pour certifier la facture FNE lors de la validation"""
        posted = super()._post(soft=soft)

        # Vérifier si la certification auto est activée
        ICP = self.env['ir.config_parameter'].sudo()
        auto_certify = ICP.get_param('l10n_ci_fne.auto_certify', 'True')

        if auto_certify == 'True':
            for move in posted:
                if move.move_type in ('out_invoice', 'out_refund') and not move.fne_certified:
                    try:
                        move._fne_certify()
                    except UserError as e:
                        # Ne pas bloquer la validation, juste logger l'erreur
                        move.fne_error_message = str(e)
                        _logger.warning("FNE: Certification échouée pour %s: %s", move.name, e)

        return posted

    def _fne_certify(self):
        """Certifie la facture auprès de la plateforme FNE"""
        self.ensure_one()

        if self.fne_certified:
            raise UserError(_("Cette facture est déjà certifiée FNE."))

        fne_api = self.env['l10n_ci_fne.api']

        if self.move_type == 'out_invoice':
            result = fne_api.certify_invoice(self)
        elif self.move_type == 'out_refund':
            # Chercher la facture d'origine
            origin_move = self.reversed_entry_id
            if origin_move and origin_move.fne_invoice_id:
                result = fne_api.certify_refund(self, origin_move.fne_invoice_id)
            else:
                raise UserError(_(
                    "FNE: Impossible de certifier l'avoir. "
                    "La facture d'origine n'a pas été certifiée FNE."
                ))
        else:
            return

        if result.get('success'):
            invoice_data = result.get('invoice_data', {})
            self.write({
                'fne_reference': result.get('reference', ''),
                'fne_token': result.get('token', ''),
                'fne_ncc': result.get('ncc', ''),
                'fne_balance_sticker': result.get('balance_sticker', 0),
                'fne_invoice_id': invoice_data.get('id', ''),
                'fne_certified': True,
                'fne_certification_date': fields.Datetime.now(),
                'fne_error_message': False,
            })

    def action_fne_certify(self):
        """Action manuelle pour certifier une facture FNE"""
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("Seule une facture validée peut être certifiée FNE."))
        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError(_("Seules les factures clients et avoirs peuvent être certifiés FNE."))
        self._fne_certify()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _('Facture certifiée FNE: %s') % self.fne_reference,
                'type': 'success',
            }
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    fne_item_id = fields.Char(
        string="ID Article FNE",
        readonly=True,
        copy=False,
        help="Identifiant de l'article sur la plateforme FNE"
    )
