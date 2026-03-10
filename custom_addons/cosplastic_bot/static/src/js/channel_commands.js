/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

// Commandes CoplasticBot
commandRegistry
    .add("aide", {
        help: _t("Affiche l'aide de l'assistant"),
        methodName: "execute_command_aide",
    })
    .add("devis", {
        help: _t("Aide pour créer un nouveau devis"),
        methodName: "execute_command_devis",
    })
    .add("client", {
        help: _t("Rechercher ou créer un client"),
        methodName: "execute_command_client",
    })
    .add("stock", {
        help: _t("Vérifier le stock d'un produit"),
        methodName: "execute_command_stock",
    })
    .add("facture", {
        help: _t("Aide pour créer une facture"),
        methodName: "execute_command_facture",
    })
    .add("commande", {
        help: _t("Aide pour créer une commande"),
        methodName: "execute_command_commande",
    })
    .add("produit", {
        help: _t("Rechercher ou gérer un produit"),
        methodName: "execute_command_produit",
    });
