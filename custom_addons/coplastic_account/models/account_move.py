# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _has_tax_lines(self):
        """Retourne True si la facture a au moins une ligne produit avec des taxes."""
        return any(
            line.tax_ids
            for line in self.invoice_line_ids
            if line.display_type == 'product'
        )

    def _get_starting_sequence(self):
        # Factures clients : FA (avec taxe) ou FAB (hors taxe)
        if self.move_type == 'out_invoice':
            prefix = 'FA' if self._has_tax_lines() else 'FAB'
            return "%s/%04d/00000" % (prefix, self.date.year)
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super()._get_last_sequence_domain(relaxed=relaxed)
        if self.move_type == 'out_invoice':
            if self._has_tax_lines():
                # Séquence FA — exclure les FAB
                where_string += " AND sequence_prefix LIKE 'FA/%%' AND sequence_prefix NOT LIKE 'FAB/%%'"
            else:
                # Séquence FAB
                where_string += " AND sequence_prefix LIKE 'FAB/%%'"
        return where_string, param
