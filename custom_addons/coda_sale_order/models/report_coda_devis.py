import base64
import os

from odoo import api, models


class ReportCodaDevis(models.AbstractModel):
    _name = 'report.coda_sale_order.report_coda_devis_document'
    _description = 'Rapport Coda Devis'

    @api.model
    def _get_report_values(self, docids, data=None):
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        def read_logo(filename):
            path = os.path.join(module_dir, 'static', 'description', filename)
            try:
                with open(path, 'rb') as f:
                    return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')
            except Exception:
                return ''

        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': self.env['sale.order'].browse(docids),
            'logo_coda': read_logo('logo_coda.png'),
            'logo_mase': read_logo('logo_mase.png'),
        }
