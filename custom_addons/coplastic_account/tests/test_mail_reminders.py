# -*- coding: utf-8 -*-
from datetime import date, timedelta
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'coplastic_account')
class TestMailReminders(TransactionCase):
    """Tests pour les règles d'automatisation de rappel par email."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Fournisseur Test Rappel',
            'email': 'fournisseur@test.com',
        })
        cls.internal_user = cls.env['res.users'].search(
            [('share', '=', False)], limit=1
        )
        cls.vendor_journal = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.env.company.id)], limit=1
        )
        cls.account_expense = cls.env['account.account'].search(
            [('account_type', '=', 'expense'), ('company_id', '=', cls.env.company.id)], limit=1
        )

    def _create_vendor_invoice(self, due_date, paid=False):
        """Crée une facture fournisseur confirmée avec une date d'échéance donnée."""
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.vendor_journal.id,
            'invoice_date': due_date - timedelta(days=30),
            'invoice_date_due': due_date,
            'invoice_user_id': self.internal_user.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Service test',
                'quantity': 1,
                'price_unit': 500.0,
                'account_id': self.account_expense.id,
            })],
        })
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # Tests règles d'automatisation
    # ------------------------------------------------------------------

    def test_01_automation_rules_exist(self):
        """Les deux règles d'automatisation doivent être installées et actives."""
        rule_invoice = self.env.ref(
            'coplastic_account.automation_vendor_invoice_overdue', raise_if_not_found=False
        )
        rule_po = self.env.ref(
            'coplastic_account.automation_po_overdue', raise_if_not_found=False
        )
        self.assertTrue(rule_invoice, "Règle automation facture fournisseur introuvable")
        self.assertTrue(rule_po, "Règle automation BC fournisseur introuvable")
        self.assertTrue(rule_invoice.active, "Règle automation facture doit être active")
        self.assertTrue(rule_po.active, "Règle automation BC doit être active")

    def test_02_automation_rule_has_action(self):
        """Chaque règle doit avoir une action serveur liée."""
        rule_invoice = self.env.ref('coplastic_account.automation_vendor_invoice_overdue')
        rule_po = self.env.ref('coplastic_account.automation_po_overdue')
        self.assertTrue(rule_invoice.action_server_ids,
            "La règle facture doit avoir au moins une action serveur")
        self.assertTrue(rule_po.action_server_ids,
            "La règle BC doit avoir au moins une action serveur")

    def test_03_automation_trigger_is_on_time(self):
        """Les règles doivent se déclencher sur condition de date."""
        rule_invoice = self.env.ref('coplastic_account.automation_vendor_invoice_overdue')
        rule_po = self.env.ref('coplastic_account.automation_po_overdue')
        self.assertEqual(rule_invoice.trigger, 'on_time',
            "Le trigger de la règle facture doit être 'on_time'")
        self.assertEqual(rule_po.trigger, 'on_time',
            "Le trigger de la règle BC doit être 'on_time'")

    def test_04_overdue_invoice_matches_filter(self):
        """Une facture échue non payée doit correspondre au filtre de la règle."""
        due_date = date.today() - timedelta(days=2)
        invoice = self._create_vendor_invoice(due_date)

        rule = self.env.ref('coplastic_account.automation_vendor_invoice_overdue')
        domain = rule._get_filter_domain()
        matching = self.env['account.move'].search(domain)
        self.assertIn(invoice, matching,
            "La facture échue non payée doit correspondre au filtre de la règle")

    def test_05_paid_invoice_does_not_match_filter(self):
        """Une facture payée ne doit PAS correspondre au filtre de la règle."""
        due_date = date.today() - timedelta(days=2)
        invoice = self._create_vendor_invoice(due_date)

        # Payer la facture
        self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({}).action_create_payments()

        rule = self.env.ref('coplastic_account.automation_vendor_invoice_overdue')
        domain = rule._get_filter_domain()
        matching = self.env['account.move'].search(domain)
        self.assertNotIn(invoice, matching,
            "Une facture payée ne doit pas correspondre au filtre de la règle")

    def test_06_email_templates_exist(self):
        """Les templates email doivent être présents."""
        tmpl_invoice = self.env.ref(
            'coplastic_account.email_template_vendor_invoice_overdue', raise_if_not_found=False
        )
        tmpl_po = self.env.ref(
            'coplastic_account.email_template_po_overdue', raise_if_not_found=False
        )
        self.assertTrue(tmpl_invoice, "Template email facture fournisseur introuvable")
        self.assertTrue(tmpl_po, "Template email BC fournisseur introuvable")
