/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { Component, useRef } from "@odoo/owl";

/**
 * Bouton « Certifier FNE » / « Imprimer FNE » de l'écran Commandes.
 *
 * Un ticket de caisse n'est normalisé qu'à la demande : ce bouton déclenche la
 * certification auprès de la DGI si elle n'a pas encore eu lieu, puis
 * (ré)imprime le ticket, qui porte alors le bloc FNE.
 */
export class FneReceiptButton extends Component {
    static template = "l10n_ci_fne_pos.FneReceiptButton";

    setup() {
        this.pos = usePos();
        this.fneButton = useRef("fne-button");
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.printer = useService("printer");
    }

    get isCertified() {
        return Boolean(this.props.order?.fne_certified);
    }

    get commandName() {
        return this.isCertified ? _t("Imprimer FNE") : _t("Certifier FNE");
    }

    async _printFneReceipt() {
        const order = this.props.order;
        if (!order) {
            return;
        }

        // La certification est faite côté serveur : c'est lui qui parle à la
        // DGI et qui stocke la référence. On récupère les données à imprimer.
        const fneData = await this.orm.call("pos.order", "fne_certify_from_ui", [
            order.backendId,
        ]);
        Object.assign(order, fneData);
        // Active le bloc FNE pour cette impression uniquement.
        order.fne_display = true;

        // printer.print() renvoie false quand aucune imprimante thermique n'est
        // configurée : on retombe alors sur l'écran de reçu, qui affiche le
        // ticket et propose l'impression navigateur. Même comportement que le
        // bouton « Imprimer le ticket » d'Odoo.
        const printed = await this.printer.print(OrderReceipt, {
            data: order.export_for_printing(),
            formatCurrency: this.env.utils.formatCurrency,
        });
        if (!printed) {
            this.pos.showScreen("ReprintReceiptScreen", { order });
        }
    }

    async click() {
        try {
            this.fneButton.el.style.pointerEvents = "none";
            await this._printFneReceipt();
        } catch (error) {
            // Une certification refusée par la DGI ne doit pas bloquer la
            // caisse : on affiche le motif et on laisse le caissier continuer.
            this.popup.add(ErrorPopup, {
                title: _t("Certification FNE impossible"),
                body: error?.data?.message || error?.message || _t("Erreur inconnue."),
            });
        } finally {
            this.fneButton.el.style.pointerEvents = "auto";
        }
    }
}
