from odoo import models, fields

COLS = [(chr(c), chr(c)) for c in range(ord('A'), ord('Z') + 1)]
_NONE = [('', '— Aucune —')]


class SaleOrderImportConfig(models.Model):
    _name = 'sale.order.import.config'
    _description = "Configuration d'import Excel (sauvegardée)"
    _order = 'name'

    name = fields.Char(string='Nom', required=True)

    skip_rows = fields.Integer(string="Lignes d'en-tête à ignorer", default=2)
    read_coefficient = fields.Boolean(string='Lire le coefficient (ligne 1)', default=True)
    col_coefficient = fields.Char(string='Colonne coefficient', default='D')
    read_numero_da = fields.Boolean(string='Lire le N° DA (dernière ligne)', default=True)

    ref_field = fields.Selection(
        [('default_code', 'Référence interne'), ('name', 'Nom du produit')],
        string='Identifier le produit par',
        default='name',
        required=True,
    )
    create_missing_products = fields.Boolean(string='Créer les produits manquants', default=False)

    col_ref = fields.Char(string='Colonne produit', default='A', required=True)
    col_name = fields.Char(string='Colonne nom produit', default='')
    col_qty = fields.Char(string='Quantité', default='B', required=True)
    col_prix_revient = fields.Char(string='Prix de revient', default='C')
    col_price_unit = fields.Char(string='Prix de vente', default='D')
