# -*- coding: utf-8 -*-
from odoo import fields, models


class BalanceTiersReport(models.TransientModel):
    _name = 'coplastic.balance.tiers.report'
    _inherit = 'account.balance.report'
    _description = 'Balance des tiers'

    # Redéfinir les Many2many pour éviter le conflit de table avec account.balance.report
    section_report_ids = fields.Many2many(
        string="Sections",
        comodel_name='account.report',
        relation="coplastic_balance_tiers_section_rel",
        column1="main_report_id",
        column2="sub_report_id",
    )
    section_main_report_ids = fields.Many2many(
        string="Section Of",
        comodel_name='account.report',
        relation="coplastic_balance_tiers_section_rel",
        column1="sub_report_id",
        column2="main_report_id",
    )
    journal_ids = fields.Many2many(
        'account.journal',
        'coplastic_balance_tiers_journal_rel',
        'account_id',
        'journal_id',
        string='Journals',
        required=True,
        default=[],
    )
    account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='coplastic_balance_tiers_account_rel',
        column1='wizard_id',
        column2='account_id',
        string='Comptes',
        domain=[('code', 'like', '4')],
    )
    tiers_type = fields.Selection(
        selection=[
            ('all', 'Tous les tiers'),
            ('client', 'Clients (41)'),
            ('supplier', 'Fournisseurs (40)'),
        ],
        string='Type de tiers',
        default='all',
        required=True,
    )

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form']['account_ids_filter'] = self.account_ids.ids or []
        data['form']['tiers_type'] = self.tiers_type or 'all'
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'coplastic_report.action_report_balance_tiers'
        ).report_action(records, data=data)
