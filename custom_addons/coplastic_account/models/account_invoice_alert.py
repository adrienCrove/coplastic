# -*- coding: utf-8 -*-
from datetime import date, timedelta
from markupsafe import Markup
from odoo import api, models


class AccountInvoiceAlert(models.AbstractModel):
    _name = 'coplastic.account.invoice.alert'
    _description = 'Alertes échéance factures clients'

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
