# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'coplastic_account')
class TestInvoiceSequence(TransactionCase):
    """Tests pour la logique de séquence FAB/FA sur les factures clients."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Client Test Séquence'})
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.env.company.id)], limit=1
        )
        cls.tax = cls.env['account.tax'].search(
            [('type_tax_use', '=', 'sale'), ('company_id', '=', cls.env.company.id)], limit=1
        )
        cls.account_income = cls.env['account.account'].search(
            [('account_type', '=', 'income'), ('company_id', '=', cls.env.company.id)], limit=1
        )

    def _create_posted_invoice(self, with_tax=False):
        """Crée et confirme une facture client, avec ou sans taxe."""
        line_vals = {
            'name': 'Produit test',
            'quantity': 1,
            'price_unit': 100.0,
            'account_id': self.account_income.id,
            'tax_ids': [(6, 0, [self.tax.id])] if with_tax else [(5, 0, 0)],
        }
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        })
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # Tests séquence
    # ------------------------------------------------------------------

    def test_01_invoice_with_tax_starts_with_fa(self):
        """Une facture avec taxe doit avoir un numéro FA/YYYY/XXXXX."""
        invoice = self._create_posted_invoice(with_tax=True)
        self.assertTrue(
            invoice.name.startswith('FA/'),
            f"Séquence attendue FA/..., obtenu : {invoice.name}"
        )

    def test_02_invoice_without_tax_starts_with_fab(self):
        """Une facture hors taxe doit avoir un numéro FAB/YYYY/XXXXX."""
        invoice = self._create_posted_invoice(with_tax=False)
        self.assertTrue(
            invoice.name.startswith('FAB/'),
            f"Séquence attendue FAB/..., obtenu : {invoice.name}"
        )

    def test_03_fa_and_fab_counters_are_independent(self):
        """Les compteurs FA et FAB sont indépendants (FAB/1 ne suit pas FA/1)."""
        inv_tax1 = self._create_posted_invoice(with_tax=True)
        inv_tax2 = self._create_posted_invoice(with_tax=True)
        inv_notax1 = self._create_posted_invoice(with_tax=False)

        # FA doit être incrémenté
        num_tax1 = int(inv_tax1.name.split('/')[-1])
        num_tax2 = int(inv_tax2.name.split('/')[-1])
        self.assertEqual(num_tax2, num_tax1 + 1,
            f"FA devrait s'incrémenter : {inv_tax1.name} → {inv_tax2.name}")

        # FAB démarre à 1 (indépendant de FA)
        num_notax1 = int(inv_notax1.name.split('/')[-1])
        self.assertEqual(num_notax1, 1,
            f"FAB devrait démarrer à 1, obtenu : {inv_notax1.name}")

    def test_04_fa_sequence_format(self):
        """Le format doit être FA/YYYY/NNNNN."""
        invoice = self._create_posted_invoice(with_tax=True)
        parts = invoice.name.split('/')
        self.assertEqual(len(parts), 3,
            f"Format attendu FA/YYYY/NNNNN, obtenu : {invoice.name}")
        self.assertEqual(parts[0], 'FA')
        self.assertTrue(parts[1].isdigit() and len(parts[1]) == 4,
            f"L'année doit être sur 4 chiffres, obtenu : {parts[1]}")

    def test_05_vendor_invoice_not_affected(self):
        """Les factures fournisseurs ne doivent PAS utiliser FA/FAB."""
        vendor_journal = self.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1
        )
        account_expense = self.env['account.account'].search(
            [('account_type', '=', 'expense'), ('company_id', '=', self.env.company.id)], limit=1
        )
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'journal_id': vendor_journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Achat test',
                'quantity': 1,
                'price_unit': 50.0,
                'account_id': account_expense.id,
            })],
        })
        move.action_post()
        self.assertFalse(
            move.name.startswith('FA/') or move.name.startswith('FAB/'),
            f"Facture fournisseur ne doit pas utiliser FA/FAB, obtenu : {move.name}"
        )
