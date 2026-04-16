# -*- coding: utf-8 -*-
{
    'name': 'Coplastic - Comptabilité',
    'version': '17.0.1.0.0',
    'summary': 'Personnalisations comptabilité et facturation pour Coplastic',
    'category': 'Accounting',
    'author': 'Coplastic',
    'depends': ['account', 'purchase', 'base_automation', 'base_accounting_kit'],
    'data': [
        'data/mail_reminders.xml',
        'data/invoice_alert_cron.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
