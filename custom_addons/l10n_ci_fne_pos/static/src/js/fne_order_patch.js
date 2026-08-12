/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

/**
 * Champs FNE transportés du serveur jusqu'au ticket imprimé.
 * Alimentés par pos.order._fne_export_for_printing() côté Python.
 */
export const FNE_RECEIPT_FIELDS = [
    "fne_certified",
    "fne_simulation",
    "fne_reference",
    "fne_ncc",
    "fne_qr_code",
    "fne_certification_date",
];

patch(Order.prototype, {
    /** Conserve les données FNE d'une commande rechargée depuis le serveur,
     *  sans quoi la réimpression perdrait la référence et le QR code. */
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        for (const field of FNE_RECEIPT_FIELDS) {
            this[field] = json[field];
        }
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        for (const field of FNE_RECEIPT_FIELDS) {
            result[field] = this[field];
        }
        // Drapeau non persisté, positionné par le bouton qui déclenche
        // l'impression : le ticket de caisse ordinaire reste ordinaire même
        // une fois le reçu normalisé auprès de la DGI.
        result.fne_display = Boolean(this.fne_display);
        return result;
    },
});
