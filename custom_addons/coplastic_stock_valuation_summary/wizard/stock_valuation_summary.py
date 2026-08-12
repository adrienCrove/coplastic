# -*- coding: utf-8 -*-

from odoo import fields, models


class StockValuationSummaryWizard(models.TransientModel):
    _name = "stock.valuation.summary.wizard"
    _description = "Résumé valorisation de stock"

    methode = fields.Selection(
        selection=[
            ("restant", "Stock restant actuel (valeur en stock aujourd'hui)"),
            ("cumul", "Cumul des mouvements jusqu'à la date choisie"),
        ],
        string="Méthode de calcul",
        default="restant",
        required=True,
        help="• Stock restant actuel : la valeur du stock encore présent aujourd'hui "
             "(ignore la date).\n"
             "• Cumul des mouvements : additionne toutes les entrées/sorties jusqu'à "
             "la date choisie (valeur comptable à cette date).",
    )
    date_to = fields.Date(
        string="Valorisation à la date",
        default=fields.Date.context_today,
        help="Utilisée uniquement avec la méthode « Cumul des mouvements ».",
    )
    perimetre = fields.Selection(
        selection=[
            ("tous", "Tous les produits"),
            ("pf", "Produits finis (PF) uniquement"),
            ("mp", "Matières premières (MP) uniquement"),
        ],
        string="Périmètre",
        default="tous",
        required=True,
    )
    include_zero = fields.Boolean(
        string="Inclure les produits à stock nul",
        default=True,
        help="Décochez pour n'afficher que les produits ayant encore du stock.",
    )

    def action_print_xlsx(self):
        self.ensure_one()
        return self.env.ref(
            "coplastic_stock_valuation_summary."
            "action_report_stock_valuation_summary_xlsx"
        ).report_action(self)
