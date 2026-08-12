/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";

/**
 * « Imprimer le ticket » doit rester le ticket de caisse ordinaire, même
 * lorsque la commande a été normalisée auprès de la DGI. On désactive donc le
 * bloc FNE avant l'impression : seul le bouton FNE le rallume.
 */
patch(ReprintReceiptButton.prototype, {
    async click() {
        if (this.props.order) {
            this.props.order.fne_display = false;
        }
        return super.click(...arguments);
    },
});
