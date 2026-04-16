/** @odoo-module **/

/**
 * Coplastic - Navigation Enter = Tab dans les listes éditables
 */

const FOCUSABLE = [
    'input:not([type="hidden"]):not([disabled]):not([readonly])',
    'select:not([disabled])',
].join(', ');

function focusInput(input) {
    input.focus();
    if (input.select) input.select();
}

document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Enter' || ev.ctrlKey || ev.altKey || ev.metaKey) return;

    const target = ev.target;
    const row = target.closest('.o_data_row');
    if (!row) return;
    if (['TEXTAREA', 'BUTTON', 'A'].includes(target.tagName)) return;

    const tbody = row.closest('tbody');
    if (!tbody) return;

    const currentCell = target.closest('td');
    if (!currentCell) return;

    ev.preventDefault();
    ev.stopImmediatePropagation();

    // -- 1. Chercher le prochain input dans la même ligne --
    const cells = Array.from(row.querySelectorAll('td'));
    const startIdx = cells.indexOf(currentCell);

    for (let i = startIdx + 1; i < cells.length; i++) {
        const cell = cells[i];
        const input = cell.querySelector(FOCUSABLE);
        if (input) { focusInput(input); return; }

        const widget = cell.querySelector('.o_field_widget:not(.o_readonly)');
        if (widget) {
            const wi = widget.querySelector('input');
            if (wi) { focusInput(wi); return; }
        }
    }

    // -- 2. Fin de ligne : aller au premier input de la ligne suivante --
    // Pour les listes always-editable (lignes de commande), tous les inputs
    // sont déjà dans le DOM — on focuse directement sans cliquer.
    const allRows = Array.from(tbody.querySelectorAll('.o_data_row'));
    const rowIdx = allRows.indexOf(row);
    if (rowIdx + 1 >= allRows.length) return;

    const nextRow = allRows[rowIdx + 1];
    const firstInput = nextRow.querySelector(FOCUSABLE);
    if (firstInput) {
        focusInput(firstInput);
        return;
    }

    // Fallback : la ligne n'est pas encore éditable → clic pour l'activer
    const firstCell = nextRow.querySelector(
        'td:not(.o_list_record_selector):not(.o_handle_cell):not(.o_list_actions_cell)'
    );
    if (firstCell) {
        firstCell.click();
        setTimeout(function () {
            const input = nextRow.querySelector(FOCUSABLE);
            if (input) focusInput(input);
        }, 80);
    }

}, true);
