# -*- coding: utf-8 -*-
from datetime import date, timedelta
from markupsafe import Markup
from odoo import api, models


class AccountInvoiceAlert(models.AbstractModel):
    _name = 'coplastic.account.invoice.alert'
    _description = 'Alertes échéance factures et commandes clients'

    @api.model
    def _run_sale_order_due_alerts(self):
        """Cron quotidien : alerte canal Discuss + email pour les commandes clients
        dont une échéance calculée (date_order + payment_term) tombe dans N jours."""
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'coplastic_account.sale_order_alert_days', 2))
        target_date = date.today() + timedelta(days=days)

        orders = self.env['sale.order'].search([
            ('state', '=', 'sale'),
            ('payment_term_id', '!=', False),
            ('invoice_status', '!=', 'invoiced'),
        ])

        channel = self.env.ref(
            'coplastic_account.channel_alertes_devis',
            raise_if_not_found=False,
        )
        if not channel:
            channel = self.env['discuss.channel'].sudo().create({
                'name': 'Alertes Devis',
                'channel_type': 'channel',
            })

        template = self.env.ref(
            'coplastic_account.email_template_sale_order_due_soon',
            raise_if_not_found=False,
        )

        for order in orders:
            due_dates = self._compute_sale_order_due_dates(order)
            if target_date not in due_dates:
                continue

            # Email au commercial responsable
            if template and order.user_id.email:
                template.send_mail(
                    order.id,
                    force_send=True,
                    email_values={'no_auto_thread': True},
                )

            # Notification dans le canal Alertes Devis
            user = order.user_id
            due_dates_str = ', '.join(str(d) for d in sorted(due_dates))
            body = Markup(
                '<p><b>&#9888; Commande bientôt échue (J-{days})</b></p>'
                '<ul>'
                '<li>Commande : <b>{link}</b></li>'
                '<li>Client : {partner}</li>'
                '<li>Conditions : {term}</li>'
                '<li>Échéance(s) : <b>{dues}</b></li>'
                '<li>Montant total : <b>{amount} {currency}</b></li>'
                '</ul>'
                '{responsable}'
            ).format(
                days=days,
                link=order._get_html_link(),
                partner=order.partner_id.name or '',
                term=order.payment_term_id.name or '',
                dues=due_dates_str,
                amount=order.amount_total,
                currency=order.currency_id.name or '',
                responsable=Markup(
                    '<p>Responsable : {}, merci de procéder à la facturation.</p>'
                ).format(user.name) if user else Markup(''),
            )
            channel.sudo().message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=user.partner_id.ids if user else [],
            )

    def _compute_sale_order_due_dates(self, order):
        """Calcule les dates d'échéance d'une commande via ses conditions de paiement."""
        if not order.payment_term_id:
            return set()
        date_ref = order.date_order.date() if order.date_order else date.today()
        terms = order.payment_term_id._compute_terms(
            date_ref=date_ref,
            currency=order.currency_id,
            company=order.company_id,
            tax_amount=order.amount_tax,
            tax_amount_currency=order.amount_tax,
            sign=1,
            untaxed_amount=order.amount_untaxed,
            untaxed_amount_currency=order.amount_untaxed,
        )
        return {line['date'] for line in terms}

    @api.model
    def _run_due_soon_alerts(self):
        """Cron quotidien : envoie email + notification canal pour les factures
        clients dont l'échéance est dans N jours (configurable dans les settings)."""
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'coplastic_account.invoice_alert_days', 5))
        target_date = date.today() + timedelta(days=days)

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed', 'in_payment']),
            ('invoice_date_due', '=', target_date),
        ])

        if not invoices:
            return

        template = self.env.ref(
            'coplastic_account.email_template_customer_invoice_due_soon',
            raise_if_not_found=False,
        )
        channel = self.env.ref(
            'coplastic_account.channel_alertes_facturation',
            raise_if_not_found=False,
        )
        if not channel:
            channel = self.env['discuss.channel'].sudo().create({
                'name': 'Alertes Facturation',
                'channel_type': 'channel',
            })

        for invoice in invoices:
            # Email au commercial responsable
            if template and invoice.invoice_user_id.email:
                template.send_mail(
                    invoice.id,
                    force_send=True,
                    email_values={'no_auto_thread': True},
                )

            # Notification dans le canal Discuss
            user = invoice.invoice_user_id
            body = Markup(
                '<p><b>&#9888; Facture bientôt échue (J-{days})</b></p>'
                '<ul>'
                '<li>Facture : <b>{link}</b></li>'
                '<li>Client : {partner}</li>'
                '<li>Échéance : <b>{due}</b></li>'
                '<li>Montant dû : <b>{amount} {currency}</b></li>'
                '</ul>'
                '{responsable}'
            ).format(
                days=days,
                link=invoice._get_html_link(),
                partner=invoice.partner_id.name or '',
                due=invoice.invoice_date_due,
                amount=invoice.amount_residual,
                currency=invoice.currency_id.name or '',
                responsable=Markup(
                    '<p>Responsable : {}, merci de relancer le client.</p>'
                ).format(user.name) if user else Markup(''),
            )
            channel.sudo().message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=user.partner_id.ids if user else [],
            )
