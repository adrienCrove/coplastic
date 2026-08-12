# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CoplasticVatClosing(models.Model):
    _name = 'coplastic.vat.closing'
    _description = "Clôture / Déclaration TVA"
    _order = 'date_to desc, id desc'

    name = fields.Char(string="Référence", default='/', copy=False, readonly=True)
    company_id = fields.Many2one(
        'res.company', string="Société", required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    date_from = fields.Date(string="Du", required=True)
    date_to = fields.Date(string="Au", required=True)

    journal_id = fields.Many2one(
        'account.journal', string="Journal (OD)",
        domain="[('type', '=', 'general')]",
        default=lambda self: self._default_journal())

    # Comptes SYSCOHADA (résolus par code, modifiables au besoin)
    account_collected_id = fields.Many2one(
        'account.account', string="Compte TVA collectée",
        default=lambda self: self._default_account('443100'))
    account_deductible_prefix = fields.Char(
        string="Préfixe comptes TVA déductible", default='445')
    account_due_id = fields.Many2one(
        'account.account', string="Compte TVA à décaisser",
        default=lambda self: self._default_account('444100'))
    account_credit_carry_id = fields.Many2one(
        'account.account', string="Compte crédit de TVA à reporter",
        default=lambda self: self._default_account('444900'))

    state = fields.Selection([
        ('draft', "Brouillon"),
        ('posted', "Écriture générée"),
    ], string="État", default='draft', copy=False)

    move_id = fields.Many2one('account.move', string="Écriture de clôture",
                              readonly=True, copy=False)

    amount_collected = fields.Monetary(string="TVA collectée", compute='_compute_amounts')
    amount_deductible = fields.Monetary(string="TVA déductible", compute='_compute_amounts')
    amount_previous_credit = fields.Monetary(string="Crédit TVA antérieur", compute='_compute_amounts')
    amount_net = fields.Monetary(string="Net", compute='_compute_amounts')
    amount_to_pay = fields.Monetary(string="TVA à décaisser", compute='_compute_amounts')
    amount_credit_carry = fields.Monetary(string="Crédit à reporter", compute='_compute_amounts')

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.env.company.id)],
            order='id', limit=1)

    @api.model
    def _default_account(self, code):
        return self.env['account.account'].search(
            [('code', '=', code), ('company_id', '=', self.env.company.id)], limit=1)

    def _deductible_accounts(self):
        self.ensure_one()
        prefix = (self.account_deductible_prefix or '445').strip()
        return self.env['account.account'].search([
            ('code', '=like', prefix + '%'),
            ('company_id', '=', self.company_id.id),
        ])

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('date_from', 'date_to', 'company_id',
                 'account_collected_id', 'account_deductible_prefix',
                 'account_credit_carry_id')
    def _compute_amounts(self):
        for rec in self:
            collected = deductible = previous = 0.0
            if rec.date_from and rec.date_to and rec.company_id:
                collected = rec._period_balance(
                    rec.account_collected_id, rec.date_from, rec.date_to, sign='credit')
                ded_accounts = rec._deductible_accounts()
                deductible = rec._period_balance(
                    ded_accounts, rec.date_from, rec.date_to, sign='debit')
                if rec.account_credit_carry_id:
                    # crédit reporté = solde débiteur du 444900 AVANT la période
                    previous = rec._period_balance(
                        rec.account_credit_carry_id, False, rec.date_from,
                        sign='debit', strict_before=True)
            net = collected - deductible - previous
            rec.amount_collected = collected
            rec.amount_deductible = deductible
            rec.amount_previous_credit = previous
            rec.amount_net = net
            rec.amount_to_pay = net if net > 0 else 0.0
            rec.amount_credit_carry = -net if net < 0 else 0.0

    def _period_balance(self, accounts, date_from, date_to, sign='debit', strict_before=False):
        """Somme (débit-crédit) ou (crédit-débit) des lignes postées sur `accounts`."""
        if not accounts:
            return 0.0
        domain = [
            ('account_id', 'in', accounts.ids),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            op = '<' if strict_before else '<='
            domain.append(('date', op, date_to))
        lines = self.env['account.move.line'].search(domain)
        debit = sum(lines.mapped('debit'))
        credit = sum(lines.mapped('credit'))
        return (debit - credit) if sign == 'debit' else (credit - debit)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'coplastic.vat.closing') or '/'
        return super().create(vals_list)

    def action_generate_move(self):
        self.ensure_one()
        if self.move_id:
            raise UserError(_("Une écriture de clôture existe déjà pour cette déclaration."))
        if not self.journal_id:
            raise UserError(_("Veuillez sélectionner un journal (OD)."))
        if not (self.account_collected_id and self.account_due_id and self.account_credit_carry_id):
            raise UserError(_("Comptes de TVA (443100 / 444100 / 444900) introuvables. Vérifiez la configuration."))

        cur = self.company_id.currency_id
        lines = []
        label = _("Clôture TVA %(from)s → %(to)s") % {
            'from': self.date_from, 'to': self.date_to}

        # 1. Solder la TVA collectée (443100) : débit
        if not cur.is_zero(self.amount_collected):
            lines.append((0, 0, {
                'account_id': self.account_collected_id.id,
                'name': label,
                'debit': self.amount_collected if self.amount_collected > 0 else 0.0,
                'credit': -self.amount_collected if self.amount_collected < 0 else 0.0,
            }))

        # 2. Solder chaque compte de TVA déductible (445xxx) : crédit
        for acc in self._deductible_accounts():
            bal = self._period_balance(acc, self.date_from, self.date_to, sign='debit')
            if not cur.is_zero(bal):
                lines.append((0, 0, {
                    'account_id': acc.id,
                    'name': label,
                    'debit': -bal if bal < 0 else 0.0,
                    'credit': bal if bal > 0 else 0.0,
                }))

        # 3. Solder le crédit de TVA antérieur (444900) : crédit (on le consomme)
        if not cur.is_zero(self.amount_previous_credit):
            lines.append((0, 0, {
                'account_id': self.account_credit_carry_id.id,
                'name': _("Imputation crédit TVA antérieur"),
                'debit': 0.0,
                'credit': self.amount_previous_credit,
            }))

        # 4. Résultat : TVA à décaisser (444100 crédit) ou nouveau crédit (444900 débit)
        if not cur.is_zero(self.amount_to_pay):
            lines.append((0, 0, {
                'account_id': self.account_due_id.id,
                'name': _("TVA à décaisser"),
                'debit': 0.0,
                'credit': self.amount_to_pay,
            }))
        elif not cur.is_zero(self.amount_credit_carry):
            lines.append((0, 0, {
                'account_id': self.account_credit_carry_id.id,
                'name': _("Crédit de TVA à reporter"),
                'debit': self.amount_credit_carry,
                'credit': 0.0,
            }))

        if not lines:
            raise UserError(_("Aucun mouvement de TVA sur la période : rien à clôturer."))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'ref': self.name,
            'company_id': self.company_id.id,
            'line_ids': lines,
        })
        self.move_id = move.id
        self.state = 'posted'
        return self.action_view_move()

    def action_view_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == 'posted':
                raise UserError(_("L'écriture est déjà comptabilisée ; annulez-la d'abord dans le journal."))
            if rec.move_id:
                rec.move_id.unlink()
            rec.state = 'draft'
