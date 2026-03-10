import logging
from odoo import models
from odoo.addons.account.models.chart_template import TEMPLATE_MODELS

_logger = logging.getLogger(__name__)

# Ensure processing order: accounts before tax groups
_LOAD_ORDER = ['res.company'] + list(TEMPLATE_MODELS)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_chart_template_data(self, template_code):
        """Override to log what _get_chart_template_data returns."""
        result = super()._get_chart_template_data(template_code)
        account_count = len(result.get('account.account', {}))
        _logger.info(
            "coplastic_account_fix: _get_chart_template_data('%s') returned keys=%s, "
            "account.account count=%d, template_register['ci'] models=%s",
            template_code,
            list(result.keys()),
            account_count,
            list(self._template_register.get('ci', {}).keys()),
        )
        return result

    def _load_data(self, data, ignore_duplicates=False):
        """Reorder data dict to enforce TEMPLATE_MODELS processing order.

        Root cause of bug: in _get_chart_template_data, 'account.tax.group' key
        is inserted into template_data BEFORE 'account.account' because
        account.tax.group-ci.csv exists in l10n_ci (early key creation) while
        account.account-ci.csv does NOT exist (key only created later via code='ci'
        using l10n_syscohada CSV).

        Resulting broken order: res.company -> account.tax.group -> account.tax -> account.account
        Fixed order:            res.company -> account.account -> account.tax.group -> account.tax

        Without this fix, deref_values() for account.tax tries to ref() accounts
        that haven't been created yet -> ValueError: External ID not found.
        """
        account_count = len(data.get('account.account', {}))
        _logger.info(
            "coplastic_account_fix: _load_data input keys=%s, account.account=%d entries",
            list(data.keys()), account_count
        )
        ordered = {key: data[key] for key in _LOAD_ORDER if key in data}
        for key in data:
            if key not in ordered:
                ordered[key] = data[key]
        _logger.info(
            "coplastic_account_fix: _load_data reordered keys: %s",
            list(ordered.keys())
        )
        return super()._load_data(ordered, ignore_duplicates=ignore_duplicates)
