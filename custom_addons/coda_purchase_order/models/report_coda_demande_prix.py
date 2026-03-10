import base64
import os

from odoo import api, models


class ReportCodaDemandePrix(models.AbstractModel):
    _name = 'report.coda_purchase_order.report_coda_demande_prix_document'
    _description = 'Rapport Coda Demande de Prix'

    @api.model
    def _get_report_values(self, docids, data=None):
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        def read_logo(filename):
            path = os.path.join(module_dir, 'static', 'src', filename)
            try:
                with open(path, 'rb') as f:
                    return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')
            except Exception:
                return ''

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': self.env['purchase.order'].browse(docids),
            'logo_coda': read_logo('logo_coda.png'),
            'logo_mase': read_logo('logo_mase.png'),
        }
