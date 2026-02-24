# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    auto_reconcile = fields.Boolean(
        string="Rapprochement automatique",
        default=False,
        help="Si activé, lors de la validation d'un paiement, une écriture de rapprochement "
             "sera automatiquement créée pour solder le compte de paiements en suspens "
             "et mouvementer le compte réel de la banque ou de la caisse.",
    )
