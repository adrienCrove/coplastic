from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain
            company = m.company_id or self.env.company
            domain = [*self.env['account.journal']._check_company_domain(company)]
            if journal_type:
                domain.append(('type', '=', journal_type))
            m.suitable_journal_ids = self.env['account.journal'].search(domain)
