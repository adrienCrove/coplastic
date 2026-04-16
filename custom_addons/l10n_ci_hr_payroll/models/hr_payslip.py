# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @staticmethod
    def _l10n_ci_compute_its(brut_mensuel):
        """
        Calcule l'ITS brut mensuel selon le barème 2024 (réforme Ordonnance 2023-719).

        :param brut_mensuel: Revenu brut mensuel imposable en FCFA
        :return: Montant ITS brut mensuel en FCFA (avant RICF)
        """
        tranches = [
            (75000, 0),
            (240000, 16),
            (800000, 21),
            (2400000, 24),
            (8000000, 28),
            (float('inf'), 32),
        ]

        impot = 0
        borne_inf = 0
        for borne_sup, taux in tranches:
            if brut_mensuel <= borne_inf:
                break
            tranche_imposable = min(brut_mensuel, borne_sup) - borne_inf
            if tranche_imposable > 0:
                impot += tranche_imposable * taux / 100
            borne_inf = borne_sup

        return round(impot)

    @staticmethod
    def _l10n_ci_compute_ricf(parts_igr):
        """
        Calcule la RICF (Réduction d'Impôt pour Charges de Famille).
        Barème 2024 : 5 500 FCFA par demi-part au-delà de 1, plafonné à 5 parts.

        :param parts_igr: Nombre de parts IGR
        :return: Montant RICF mensuel en FCFA
        """
        parts = min(max(parts_igr, 1.0), 5.0)
        return round((parts - 1) * 11000)

    def _l10n_ci_check_contract_period(self):
        """Vérifie que la période du bulletin n'est pas antérieure au contrat."""
        check = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_ci_hr_payroll.check_contract_dates', default='False'
        )
        if check != 'True':
            return
        for slip in self:
            contract = slip.contract_id
            if contract and contract.date_start and contract.date_start > slip.date_from:
                raise UserError(
                    _("Impossible de traiter le bulletin « %s » :\n"
                      "La période %s → %s est antérieure à la date de début "
                      "du contrat %s (%s).\n\n"
                      "Corrigez la date de début du contrat ou supprimez ce bulletin.")
                    % (
                        slip.name or slip.employee_id.name,
                        slip.date_from.strftime('%d/%m/%Y'),
                        slip.date_to.strftime('%d/%m/%Y'),
                        contract.name,
                        contract.date_start.strftime('%d/%m/%Y'),
                    )
                )

    def compute_sheet(self):
        self._l10n_ci_check_contract_period()
        return super().compute_sheet()

    def action_payslip_done(self):
        self._l10n_ci_check_contract_period()
        return super().action_payslip_done()
