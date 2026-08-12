# -*- coding: utf-8 -*-
{
    'name': 'Coplastic - Comptabilité',
    'version': '17.0.1.0.0',
    'summary': 'Personnalisations comptabilité et facturation pour Coplastic',
    'category': 'Accounting',
    'author': 'Coplastic',
    'depends': ['account', 'purchase', 'sale', 'base_automation', 'base_accounting_kit', 'base_account_budget'],
    'data': [
        'data/mail_reminders.xml',
        'data/invoice_alert_cron.xml',
        'views/res_config_settings_views.xml',
        'views/partner_ledger_wizard_views.xml',
        'views/report_wizard_views.xml',
        'views/budget_views.xml',
        'report/report_partner_ledger.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
