/** @odoo-module **/

import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { localization } from "@web/core/l10n/localization";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { ActionContainer } from "./actions/action_container";
import { NavBar } from "./navbar/navbar";
import { HomeDashboard } from "./home_dashboard/home_dashboard";

import { Component, onMounted, useExternalListener, useState } from "@odoo/owl";

export class WebClient extends Component {
    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.title = useService("title");
        this.router = useService("router");
        this.user = useService("user");
        useService("legacy_service_provider");
        useOwnDebugContext({ categories: ["default"] });
        if (this.env.debug) {
            registry.category("systray").add(
                "web.debug_mode_menu",
                {
                    Component: DebugMenu,
                },
                { sequence: 100 }
            );
        }
        this.localization = localization;
        this.state = useState({
            fullscreen: false,
            home: false,
            openingApp: false,
        });
        this.title.setParts({ zopenerp: "Workspace" }); // zopenerp is easy to grep
        useBus(this.env.bus, "ROUTE_CHANGE", this.loadRouterState);
        useBus(this.env.bus, "WORKSPACE:HOME", this.openHome);
        useBus(this.env.bus, "WORKSPACE:APP-OPENING", () => {
            this.state.openingApp = true;
        });
        useBus(this.env.bus, "WORKSPACE:APP-OPENED", () => {
            this.state.openingApp = false;
            this.state.home = false;
        });
        useBus(this.env.bus, "WORKSPACE:APP-FAILED", () => {
            this.state.openingApp = false;
        });
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", ({ detail: mode }) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
        onMounted(() => {
            this.loadRouterState();
            // the chat window and dialog services listen to 'web_client_ready' event in
            // order to initialize themselves:
            this.env.bus.trigger("WEB_CLIENT_READY");
        });
        useExternalListener(window, "click", this.onGlobalClick, { capture: true });
    }

    openHome() {
        this.state.home = true;
        this.state.openingApp = false;
        this.state.fullscreen = false;
        this.menuService.setCurrentMenu(null);
        this.title.setParts({ action: null });
        this.router.pushState(
            {
                cids: this.router.current.hash.cids,
                menu_id: undefined,
                action: undefined,
                id: undefined,
                model: undefined,
                view_type: undefined,
            },
            { replace: true, lock: false }
        );
    }

    async loadRouterState() {
        if (this.state.openingApp && this.state.home) {
            return;
        }
        const hash = this.router.current.hash;
        const hasExplicitRoute = Boolean(
            hash.menu_id || hash.action || hash.model || hash.id || hash.view_type
        );
        if (!hasExplicitRoute) {
            this.state.home = true;
            this.state.fullscreen = false;
            this.menuService.setCurrentMenu(null);
            this.title.setParts({ action: null });
            return;
        }

        let stateLoaded = await this.actionService.loadState();
        let menuId = Number(hash.menu_id || 0);

        if (!stateLoaded && menuId) {
            // Determines the current actionId based on the current menu
            const menu = this.menuService.getAll().find((m) => menuId === m.id);
            const actionId = menu && menu.actionID;
            if (actionId) {
                await this.actionService.doAction(actionId, { clearBreadcrumbs: true });
                stateLoaded = true;
            }
        }

        if (stateLoaded && !menuId) {
            // Determines the current menu based on the current action
            const currentController = this.actionService.currentController;
            const actionId = currentController && currentController.action.id;
            const menu = this.menuService.getAll().find((m) => m.actionID === actionId);
            menuId = menu && menu.appID;
        }

        if (menuId) {
            // Sets the menu according to the current action
            this.menuService.setCurrentMenu(menuId);
        }

        this.state.home = !stateLoaded;
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev) {
        // When a ctrl-click occurs inside an <a href/> element
        // we let the browser do the default behavior and
        // we do not want any other listener to execute.
        if (
            (ev.ctrlKey || ev.metaKey) &&
            !ev.target.isContentEditable &&
            ((ev.target instanceof HTMLAnchorElement && ev.target.href) ||
                (ev.target instanceof HTMLElement && ev.target.closest("a[href]:not([href=''])")))
        ) {
            ev.stopImmediatePropagation();
            return;
        }
    }
}
WebClient.components = {
    ActionContainer,
    NavBar,
    HomeDashboard,
    MainComponentsContainer,
};
WebClient.template = "web.WebClient";
