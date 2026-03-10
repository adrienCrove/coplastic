{
    'name': 'Coplastic Account Fix',
    'version': '17.0.1.0.0',
    'summary': 'Fix chart template loading ORM flush issue in Odoo 17',
    'description': """
        Patches account.chart.template.ref() to call env.flush_all() before
        external ID lookups. This fixes the "External ID not found" error that
        occurs when loading the CI/SYSCOHADA chart template because newly created
        account records are not yet flushed to DB when tax groups reference them.
    """,
    'category': 'Accounting',
    'depends': ['account'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
