# -*- coding: utf-8 -*-
"""Helpers partagés par les documents certifiables FNE.

Factures (account.move) et tickets de caisse (pos.order) produisent la même
présentation normalisée DGI : ces fonctions évitent d'en dupliquer la logique
entre les deux modèles.
"""

import base64
import io
import logging

_logger = logging.getLogger(__name__)


def generate_qr_code(data):
    """PNG du QR code encodé en base64, ou False si la génération échoue.

    Le contenu encodé est le token de vérification renvoyé par la DGI ;
    l'image, elle, est produite localement.
    """
    if not data:
        return False
    try:
        import qrcode
    except ImportError:
        _logger.warning("Module qrcode non installé. pip install qrcode[pil]")
        return False
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.error("Erreur génération QR Code FNE: %s", e)
        return False


def format_amount(amount, precision=0):
    """Montant au format du portail FNE : espace insécable comme séparateur de
    milliers, virgule décimale, aucun symbole de devise.

    L'insécable évite qu'un montant soit coupé en fin de ligne dans le PDF."""
    formatted = '{:,.{prec}f}'.format(amount or 0.0, prec=precision)
    integer_part, _sep, decimal_part = formatted.partition('.')
    integer_part = integer_part.replace(',', '\u00a0')
    return '%s,%s' % (integer_part, decimal_part) if decimal_part else integer_part


def format_rate(rate):
    """18.0 -> '18', 9.5 -> '9.5'"""
    return '%g' % (rate or 0.0)


def format_quantity(quantity):
    """Quantité : jusqu'à 3 décimales, zéros finaux supprimés.
    Indépendant de la précision de la devise."""
    formatted = '{:,.3f}'.format(quantity or 0.0)
    integer_part, _sep, decimal_part = formatted.partition('.')
    integer_part = integer_part.replace(',', '\u00a0')
    decimal_part = decimal_part.rstrip('0')
    return '%s,%s' % (integer_part, decimal_part) if decimal_part else integer_part
