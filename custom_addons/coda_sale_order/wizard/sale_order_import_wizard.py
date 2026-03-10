import base64
import io
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

COLS = [(chr(c), chr(c)) for c in range(ord('A'), ord('Z') + 1)]
_NONE = [('', '— Aucune —')]


class SaleOrderImportWizard(models.TransientModel):
    _name = 'sale.order.import.wizard'
    _description = 'Import lignes de commande depuis Excel'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    file_data = fields.Binary(string='Fichier Excel (.xlsx)', required=True, attachment=False)
    file_name = fields.Char()

    # Template de configuration sauvegardé
    config_id = fields.Many2one(
        'sale.order.import.config',
        string='Modèle de configuration',
        help="Charger une configuration sauvegardée.",
    )

    # Lignes d'en-tête à ignorer en haut du fichier
    header_rows = fields.Integer(
        string="Lignes d'en-tête à ignorer",
        default=2,
        help="Nombre de lignes à ignorer au début du fichier.\n"
             "Exemple : 2 si la ligne 1 contient le coefficient et la ligne 2 les titres de colonnes.",
    )

    # Lecture automatique du coefficient (ex : cellule D1)
    read_coefficient = fields.Boolean(
        string='Lire le coefficient depuis la ligne 1',
        default=True,
    )
    col_coefficient = fields.Selection(
        COLS, string='Colonne coefficient (ligne 1)', default='D',
    )

    # Détection automatique du N° DA (dernière ligne)
    read_numero_da = fields.Boolean(
        string='Lire le N° DA depuis la dernière ligne',
        default=True,
    )

    # Type de recherche produit
    ref_field = fields.Selection(
        [('default_code', 'Référence interne'), ('name', 'Nom du produit')],
        string='Identifier le produit par',
        default='name',
        required=True,
    )
    create_missing_products = fields.Boolean(
        string='Créer les produits manquants',
        default=False,
    )

    # Mapping des colonnes
    col_ref = fields.Selection(
        COLS, string='Colonne produit', default='A', required=True,
    )
    col_name = fields.Selection(
        _NONE + COLS, string='Colonne nom produit', default='',
    )
    col_qty = fields.Selection(
        COLS, string='Quantité', default='B', required=True,
    )
    col_prix_revient = fields.Selection(
        _NONE + COLS, string='Prix de revient', default='C',
    )
    col_price_unit = fields.Selection(
        _NONE + COLS, string='Prix de vente', default='D',
    )

    @api.onchange('config_id')
    def _onchange_config_id(self):
        """Charge les paramètres depuis le modèle sélectionné."""
        cfg = self.config_id
        if not cfg:
            return
        self.header_rows = cfg.skip_rows or 2
        self.read_coefficient = cfg.read_coefficient
        if cfg.col_coefficient and cfg.col_coefficient.upper() in dict(COLS):
            self.col_coefficient = cfg.col_coefficient.upper()
        self.read_numero_da = cfg.read_numero_da
        self.ref_field = cfg.ref_field
        self.create_missing_products = cfg.create_missing_products
        if cfg.col_ref and cfg.col_ref.upper() in dict(COLS):
            self.col_ref = cfg.col_ref.upper()
        self.col_name = cfg.col_name.upper() if cfg.col_name and cfg.col_name.upper() in dict(COLS) else ''
        if cfg.col_qty and cfg.col_qty.upper() in dict(COLS):
            self.col_qty = cfg.col_qty.upper()
        self.col_prix_revient = cfg.col_prix_revient.upper() if cfg.col_prix_revient and cfg.col_prix_revient.upper() in dict(COLS) else ''
        self.col_price_unit = cfg.col_price_unit.upper() if cfg.col_price_unit and cfg.col_price_unit.upper() in dict(COLS) else ''

    def action_save_config(self):
        """Sauvegarde la configuration actuelle comme nouveau modèle."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sauvegarder le modèle',
            'res_model': 'sale.order.import.config.save.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_skip_rows': self.header_rows,
                'default_read_coefficient': self.read_coefficient,
                'default_col_coefficient': self.col_coefficient or 'D',
                'default_read_numero_da': self.read_numero_da,
                'default_ref_field': self.ref_field,
                'default_create_missing_products': self.create_missing_products,
                'default_col_ref': self.col_ref or 'A',
                'default_col_name': self.col_name or '',
                'default_col_qty': self.col_qty or 'B',
                'default_col_prix_revient': self.col_prix_revient or '',
                'default_col_price_unit': self.col_price_unit or '',
            },
        }

    def _get_cell(self, row, col_letter):
        if not col_letter:
            return None
        idx = ord(col_letter.upper()) - ord('A')
        if idx >= len(row):
            return None
        return row[idx]

    def _to_float(self, val, default=None):
        if val is None:
            return default
        try:
            return float(str(val).replace(',', '.').replace(' ', '').replace('\xa0', ''))
        except (ValueError, TypeError):
            return default

    def _extract_numero_da(self, row):
        for cell in row:
            if cell is None:
                continue
            text = str(cell).strip()
            if re.match(r'^DA\s*\d+', text, re.IGNORECASE):
                return text.strip()
        return None

    def _create_product(self, ref, row, prix_revient, price_unit):
        product_vals = {'type': 'consu'}
        if self.ref_field == 'name':
            product_vals['name'] = ref
        else:
            name_val = self._get_cell(row, self.col_name) if self.col_name else None
            product_vals['name'] = str(name_val).strip() if name_val else ref
            product_vals['default_code'] = ref
        if prix_revient is not None:
            product_vals['standard_price'] = prix_revient
        if price_unit is not None:
            product_vals['list_price'] = price_unit
        template = self.env['product.template'].create(product_vals)
        return template.product_variant_ids[0]

    def action_import(self):
        try:
            import openpyxl
        except ImportError:
            raise UserError("La librairie openpyxl est requise (pip install openpyxl).")

        file_content = base64.b64decode(self.file_data)
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
        except Exception as e:
            raise UserError(f"Impossible de lire le fichier Excel : {e}")

        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        if not rows:
            raise UserError("Le fichier Excel est vide.")

        # ── 1. Coefficient dans la 1ère ligne ──────────────────────────────────
        coefficient = None
        if self.read_coefficient and self.col_coefficient and rows:
            coefficient = self._to_float(self._get_cell(rows[0], self.col_coefficient))
            if coefficient:
                self.order_id.coefficient_selectivite = coefficient

        # ── 2. N° DA dans la dernière ligne non vide ───────────────────────────
        numero_da = None
        if self.read_numero_da:
            for row in reversed(rows):
                if any(c for c in row if c is not None):
                    numero_da = self._extract_numero_da(row)
                    break
            if numero_da:
                self.order_id.numero_da = numero_da

        # ── 3. Lignes de données ────────────────────────────────────────────────
        start = max(0, self.header_rows or 0)
        data_rows = list(rows[start:])

        # Exclure la dernière ligne non vide si c'est le N° DA
        if numero_da and data_rows:
            for i in range(len(data_rows) - 1, -1, -1):
                if any(c for c in data_rows[i] if c is not None):
                    if self._extract_numero_da(data_rows[i]):
                        data_rows = data_rows[:i]
                    break

        SaleLine = self.env['sale.order.line']
        errors = []
        count = 0
        created = 0

        for i, row in enumerate(data_rows, start=start + 1):
            if not any(c for c in row if c is not None):
                continue

            ref = self._get_cell(row, self.col_ref)
            if not ref:
                continue
            ref = str(ref).strip()

            qty = self._to_float(self._get_cell(row, self.col_qty), default=1.0)
            prix_revient = self._to_float(self._get_cell(row, self.col_prix_revient))
            price_unit = self._to_float(self._get_cell(row, self.col_price_unit))

            if price_unit is None and coefficient and prix_revient is not None:
                price_unit = round(prix_revient * coefficient, 2)

            product = self.env['product.product'].search(
                [(self.ref_field, '=ilike', ref)], limit=1
            )
            if not product:
                if self.create_missing_products:
                    product = self._create_product(ref, row, prix_revient, price_unit)
                    created += 1
                else:
                    label = "référence" if self.ref_field == 'default_code' else "nom"
                    errors.append(f"Ligne {i} : {label} '{ref}' introuvable dans les produits")
                    continue

            line = SaleLine.new({
                'order_id': self.order_id.id,
                'product_id': product.id,
            })
            line._onchange_product_id_prix_revient()
            line.product_uom_qty = qty
            if prix_revient is not None:
                line.prix_de_revient = prix_revient
            if price_unit is not None:
                line.price_unit = price_unit

            vals = line._convert_to_write(line._cache)
            SaleLine.create(vals)
            count += 1

        parts = [f"{count} ligne(s) importée(s) avec succès."]
        if created:
            parts.append(f"{created} produit(s) créé(s) automatiquement.")
        if coefficient:
            parts.append(f"Coefficient appliqué : {coefficient}")
        if numero_da:
            parts.append(f"N° DA récupéré : {numero_da}")

        notif_type = 'success'
        if errors:
            parts.append("\nErreurs :\n" + "\n".join(errors[:15]))
            if len(errors) > 15:
                parts.append(f"... et {len(errors) - 15} autres erreurs.")
            notif_type = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Excel',
                'message': "\n".join(parts),
                'type': notif_type,
                'sticky': bool(errors),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class SaleOrderImportConfigSaveWizard(models.TransientModel):
    """Mini-wizard pour nommer et sauvegarder un modèle de configuration."""
    _name = 'sale.order.import.config.save.wizard'
    _description = "Sauvegarder le modèle d'import"

    name = fields.Char(string='Nom du modèle', required=True)
    skip_rows = fields.Integer(default=2)
    read_coefficient = fields.Boolean(default=True)
    col_coefficient = fields.Char(default='D')
    read_numero_da = fields.Boolean(default=True)
    ref_field = fields.Selection(
        [('default_code', 'Référence interne'), ('name', 'Nom du produit')],
        default='name', required=True,
    )
    create_missing_products = fields.Boolean(default=False)
    col_ref = fields.Char(default='A')
    col_name = fields.Char(default='')
    col_qty = fields.Char(default='B')
    col_prix_revient = fields.Char(default='C')
    col_price_unit = fields.Char(default='D')

    def action_save(self):
        self.env['sale.order.import.config'].create({
            'name': self.name,
            'skip_rows': self.skip_rows,
            'read_coefficient': self.read_coefficient,
            'col_coefficient': self.col_coefficient,
            'read_numero_da': self.read_numero_da,
            'ref_field': self.ref_field,
            'create_missing_products': self.create_missing_products,
            'col_ref': self.col_ref,
            'col_name': self.col_name,
            'col_qty': self.col_qty,
            'col_prix_revient': self.col_prix_revient,
            'col_price_unit': self.col_price_unit,
        })
        return {'type': 'ir.actions.act_window_close'}
