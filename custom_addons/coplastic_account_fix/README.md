# coplastic_account_fix — Documentation

## Contexte

Ce module corrige un bug Odoo 17 qui empêche l'installation du plan comptable
Côte d'Ivoire (`l10n_ci`) sur une nouvelle base de données.

**Erreur originale :**
```
ValueError: External ID not found in the system: account.1_pcg_4431
```

---

## Symptômes

- Se produit lors de l'installation de `l10n_ci` sur une BD sans comptes comptables
- Se déclenche automatiquement via `_auto_install_template` dans `ir_module.py`
  quand la société a `account_fiscal_country_id = Côte d'Ivoire` et `chart_template = null`
- N'affecte pas une BD où `account` est réinstallé depuis zéro (seulement quand
  `account` est déjà installé et `l10n_ci` est ajouté après)

---

## Cause racine

### Le flow normal
Quand `l10n_ci` est installé, Odoo appelle automatiquement :
```
_register_hook()
  → try_loading('ci', company)
    → _load('ci', company)
      → _get_chart_template_data('ci')   # construit le dict de données
      → _pre_load_data(...)
      → _load_data(data)                 # charge tout en BD
```

### Le bug dans `_get_chart_template_data`

Cette fonction construit un `defaultdict` Python. Les clés sont insérées dans
**l'ordre où elles sont d'abord accédées**, pas dans l'ordre de `TEMPLATE_MODELS`.

Pour le template `ci`, la fonction itère sur `[None, 'ci', 'syscohada']` :

| Itération | Fichier CSV cherché | Existe ? | Effet sur le dict |
|-----------|---------------------|----------|-------------------|
| `code=None` | `l10n_ci/data/template/account.tax.group-ci.csv` | **OUI** | Clé `account.tax.group` insérée **en 1er** |
| `code=None` | `l10n_ci/data/template/account.account-ci.csv` | NON | Clé `account.account` **non insérée** |
| `code='ci'` | `l10n_syscohada/data/template/account.account-syscohada.csv` | **OUI** | Clé `account.account` insérée **tardivement** |

**Ordre résultant dans le dict :**
```
res.company → account.tax.group → account.tax → account.account
```

**Ordre attendu (TEMPLATE_MODELS) :**
```
res.company → account.account → account.tax.group → account.tax → ...
```

### Pourquoi ça plante

Dans `_load_data`, la fonction `delay()` gère les dépendances circulaires en
différant les champs qui référencent des modèles "pas encore créés"
(`yet_to_be_created_models`).

**Cas qui fonctionne :** Si `account.account` est dans `data` (même en dernier),
`delay()` le voit dans `yet_to_be_created_models` et diffère les références
des taxes vers les comptes → tout se crée dans le bon ordre.

**Cas qui plante :** Si `account.account` est **absent** de `data` (bug de
certaines configurations), `delay()` ne sait pas différer → `deref_values()`
appelle `self.ref('account.1_pcg_4431')` → compte inexistant → `ValueError`.

---

## Solution : `coplastic_account_fix`

Le module surcharge deux méthodes de `account.chart.template` :

### 1. `_get_chart_template_data` (diagnostic)
Logue les clés retournées et le nombre d'entrées `account.account` pour
faciliter le diagnostic si le bug se reproduit.

### 2. `_load_data` (correctif)
Réordonne le dict `data` reçu selon l'ordre `TEMPLATE_MODELS` avant de
passer au `super()` :

```python
_LOAD_ORDER = ['res.company', 'account.group', 'account.account',
               'account.tax.group', 'account.tax', 'account.journal',
               'account.reconcile.model', 'account.fiscal.position']
```

Cela garantit que les comptes (`account.account`) sont toujours traités
**avant** les groupes de taxes et les taxes.

---

## État actuel de `coplastic-prod`

| Élément | Valeur |
|---------|--------|
| Module `l10n_ci` | installed |
| Module `coplastic_account_fix` | installed |
| `chart_template` | `ci` (SYSCOHADA Côte d'Ivoire) |
| Comptes comptables | 1 143 (1 134 SYSCOHADA + 9 utilitaires) |
| Taxes | 13 |

---

## Procédure de résolution si ça se reproduit

### Cas 1 : Nouvelle BD avec `account` déjà installé

```bash
# Installer d'abord coplastic_account_fix, puis l10n_ci
docker exec coplastic-odoo bash -c \
  "odoo -c /etc/odoo/odoo.conf -d MA_BD -i coplastic_account_fix --stop-after-init --no-http"

docker exec coplastic-odoo bash -c \
  "odoo -c /etc/odoo/odoo.conf -d MA_BD -i l10n_ci --stop-after-init --no-http"

docker restart coplastic-odoo
```

### Cas 2 : En dernier recours (réinstallation complète)

```bash
# Forcer la réinstallation du module account et l10n_ci ensemble
docker exec coplastic-odoo bash -c \
  "odoo -c /etc/odoo/odoo.conf -d MA_BD -i account,l10n_ci --stop-after-init --no-http"

docker restart coplastic-odoo
```

---

## Fichiers du module

```
coplastic_account_fix/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── chart_template_fix.py   ← le correctif
└── README.md                    ← ce fichier
```

---

## Référence technique

- Bug dans : `/usr/lib/python3/dist-packages/odoo/addons/account/models/chart_template.py`
  - `_get_chart_template_data()` ligne ~739
  - `_load_data()` ligne ~525
- Déclencheur : `/usr/lib/python3/dist-packages/odoo/addons/account/models/ir_module.py`
  - `_register_hook()` ligne ~92
- Données SYSCOHADA : `/usr/lib/python3/dist-packages/odoo/addons/l10n_syscohada/data/template/account.account-syscohada.csv`
  (1 134 comptes)
