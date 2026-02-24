# -*- coding: utf-8 -*-

from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @staticmethod
    def _l10n_ci_compute_its(brut_imposable_annuel, parts_igr):
        """
        Calcule l'ITS (Impôt sur Traitements et Salaires) selon le barème ivoirien.

        :param brut_imposable_annuel: Revenu imposable annuel en FCFA
        :param parts_igr: Nombre de parts IGR du contribuable
        :return: Montant ITS mensuel en FCFA
        """
        # Barème progressif ITS Côte d'Ivoire
        tranches = [
            (300000, 0),
            (526000, 1.5),
            (1056000, 5),
            (1586000, 10),
            (2116000, 15),
            (2646000, 20),
            (3706000, 25),
            (5826000, 30),
            (10066000, 35),
            (13466000, 37),
            (float('inf'), 39),
        ]

        # Calcul du revenu par part
        revenu_par_part = brut_imposable_annuel / max(parts_igr, 1)

        # Calcul de l'impôt par part
        impot_par_part = 0
        borne_inf = 0
        for borne_sup, taux in tranches:
            if revenu_par_part <= borne_inf:
                break
            tranche_imposable = min(revenu_par_part, borne_sup) - borne_inf
            if tranche_imposable > 0:
                impot_par_part += tranche_imposable * taux / 100
            borne_inf = borne_sup

        # Impôt total = impôt par part * nombre de parts
        impot_annuel = impot_par_part * max(parts_igr, 1)

        # Plafond de réduction pour charges de famille
        # La réduction ne peut excéder 10% du revenu imposable
        impot_sans_parts = 0
        borne_inf = 0
        for borne_sup, taux in tranches:
            if brut_imposable_annuel <= borne_inf:
                break
            tranche_imposable = min(brut_imposable_annuel, borne_sup) - borne_inf
            if tranche_imposable > 0:
                impot_sans_parts += tranche_imposable * taux / 100
            borne_inf = borne_sup

        reduction = impot_sans_parts - impot_annuel
        max_reduction = brut_imposable_annuel * 0.10
        if reduction > max_reduction:
            impot_annuel = impot_sans_parts - max_reduction

        # ITS mensuel
        its_mensuel = round(impot_annuel / 12)
        return its_mensuel
