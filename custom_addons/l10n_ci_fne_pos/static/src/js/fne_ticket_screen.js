/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { FneReceiptButton } from "./fne_receipt_button";

// Rend le bouton FNE utilisable dans le template hérité de l'écran Commandes,
// aux côtés de InvoiceButton et ReprintReceiptButton.
TicketScreen.components = { ...TicketScreen.components, FneReceiptButton };
