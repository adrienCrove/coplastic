# -*- coding: utf-8 -*-

from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    advance_count = fields.Integer(
        string="Avances",
        compute='_compute_advance_count',
    )

    def _compute_advance_count(self):
        for slip in self:
            slip.advance_count = self.env['hr.salary.advance'].search_count([
                ('employee_id', '=', slip.employee_id.id),
                ('state', 'in', ('approved', 'done')),
            ])

    def action_view_advances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Avances sur Salaire',
            'res_model': 'hr.salary.advance',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def compute_sheet(self):
        """Injecte automatiquement les échéances d'avance dans les inputs du bulletin."""
        for slip in self:
            slip._inject_advance_inputs()
        return super().compute_sheet()

    def _inject_advance_inputs(self):
        """Cherche les échéances d'avance non payées pour l'employé et la période du bulletin."""
        self.ensure_one()
        lines = self.env['hr.salary.advance.line'].search([
            ('advance_id.employee_id', '=', self.employee_id.id),
            ('advance_id.state', '=', 'approved'),
            ('is_paid', '=', False),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ])
        if not lines:
            return

        total = sum(lines.mapped('amount'))

        # Cherche si un input CI_AVANCE existe déjà
        existing = self.input_line_ids.filtered(lambda i: i.code == 'CI_AVANCE')
        if existing:
            existing.write({'amount': total})
        else:
            self.write({
                'input_line_ids': [(0, 0, {
                    'name': 'Avance sur salaire (auto)',
                    'code': 'CI_AVANCE',
                    'amount': total,
                    'contract_id': self.contract_id.id,
                })]
            })

    def action_payslip_done(self):
        """Marque les échéances d'avance comme payées lors de la validation du bulletin."""
        res = super().action_payslip_done()
        for slip in self:
            lines = self.env['hr.salary.advance.line'].search([
                ('advance_id.employee_id', '=', slip.employee_id.id),
                ('advance_id.state', '=', 'approved'),
                ('is_paid', '=', False),
                ('date', '>=', slip.date_from),
                ('date', '<=', slip.date_to),
            ])
            lines.write({'is_paid': True, 'payslip_id': slip.id})
            lines.mapped('advance_id')._check_done()
        return res
