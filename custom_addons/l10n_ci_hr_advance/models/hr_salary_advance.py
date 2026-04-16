# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrSalaryAdvance(models.Model):
    _name = 'hr.salary.advance'
    _description = 'Avance sur Salaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string="Référence",
        readonly=True,
        default='Nouveau',
        copy=False,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employé",
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        related='employee_id.department_id',
        store=True,
    )
    company_id = fields.Many2one(
        related='employee_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
    )
    date = fields.Date(
        string="Date de la demande",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Montant de l'avance",
        required=True,
        tracking=True,
    )
    nb_mensualites = fields.Integer(
        string="Nombre de mensualités",
        default=1,
        required=True,
        help="Nombre de mois pour rembourser l'avance.",
    )
    montant_mensuel = fields.Monetary(
        string="Mensualité",
        compute='_compute_montant_mensuel',
        store=True,
    )
    montant_rembourse = fields.Monetary(
        string="Montant remboursé",
        compute='_compute_montant_rembourse',
        store=True,
    )
    solde_restant = fields.Monetary(
        string="Solde restant",
        compute='_compute_montant_rembourse',
        store=True,
    )
    reason = fields.Text(
        string="Motif",
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('approved', 'Approuvé'),
        ('done', 'Remboursé'),
        ('cancelled', 'Annulé'),
    ], default='draft', tracking=True, string="Statut")

    line_ids = fields.One2many(
        'hr.salary.advance.line',
        'advance_id',
        string="Échéances de remboursement",
    )

    @api.depends('amount', 'nb_mensualites')
    def _compute_montant_mensuel(self):
        for rec in self:
            if rec.nb_mensualites > 0:
                rec.montant_mensuel = rec.amount / rec.nb_mensualites
            else:
                rec.montant_mensuel = rec.amount

    @api.depends('line_ids.is_paid')
    def _compute_montant_rembourse(self):
        for rec in self:
            paid = sum(line.amount for line in rec.line_ids if line.is_paid)
            rec.montant_rembourse = paid
            rec.solde_restant = rec.amount - paid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.salary.advance') or 'Nouveau'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_approve(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_("Le montant de l'avance doit être supérieur à 0."))
            rec._generate_repayment_lines()
        self.write({'state': 'approved'})

    def action_cancel(self):
        for rec in self:
            if any(line.is_paid for line in rec.line_ids):
                raise UserError(_("Impossible d'annuler : des remboursements ont déjà été effectués."))
            rec.line_ids.unlink()
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        for rec in self:
            if any(line.is_paid for line in rec.line_ids):
                raise UserError(_("Impossible de remettre en brouillon : des remboursements ont déjà été effectués."))
            rec.line_ids.unlink()
        self.write({'state': 'draft'})

    def _generate_repayment_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        mensualite = round(self.amount / self.nb_mensualites)
        reste = self.amount
        date = self.date
        for i in range(self.nb_mensualites):
            montant = mensualite if i < self.nb_mensualites - 1 else reste
            self.env['hr.salary.advance.line'].create({
                'advance_id': self.id,
                'sequence': i + 1,
                'amount': montant,
                'date': date,
            })
            reste -= montant
            # Mois suivant
            month = date.month + 1
            year = date.year
            if month > 12:
                month = 1
                year += 1
            date = date.replace(year=year, month=month, day=min(date.day, 28))

    def _check_done(self):
        for rec in self:
            if rec.state == 'approved' and rec.solde_restant <= 0:
                rec.write({'state': 'done'})


class HrSalaryAdvanceLine(models.Model):
    _name = 'hr.salary.advance.line'
    _description = "Échéance de remboursement d'avance"
    _order = 'sequence'

    advance_id = fields.Many2one(
        'hr.salary.advance',
        string="Avance",
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string="N°")
    amount = fields.Monetary(
        string="Montant",
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='advance_id.currency_id',
    )
    date = fields.Date(string="Échéance")
    is_paid = fields.Boolean(string="Payé", default=False)
    payslip_id = fields.Many2one(
        'hr.payslip',
        string="Bulletin",
        readonly=True,
    )
