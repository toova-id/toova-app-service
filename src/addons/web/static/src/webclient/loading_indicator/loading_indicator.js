/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { Transition } from "@web/core/transition";

import { Component, useState } from "@odoo/owl";

/**
 * Loading Indicator
 *
 * When the user performs an action, it is good to give him some feedback that
 * something is currently happening.  The purpose of the Loading Indicator is to
 * display one centered spinner while RPCs are running.
 */
export class LoadingIndicator extends Component {
    setup() {
        this.state = useState({
            count: 0,
            show: false,
        });
        this.rpcIds = new Set();
        this.startShowTimer = null;
        useBus(this.env.bus, "RPC:REQUEST", this.requestCall);
        useBus(this.env.bus, "RPC:RESPONSE", this.responseCall);
    }

    requestCall({ detail: rpcId }) {
        if (this.state.count === 0) {
            browser.clearTimeout(this.startShowTimer);
            this.startShowTimer = browser.setTimeout(() => {
                if (this.state.count) {
                    this.state.show = true;
                }
            }, 250);
        }
        this.rpcIds.add(rpcId);
        this.state.count++;
    }

    responseCall({ detail: rpcId }) {
        this.rpcIds.delete(rpcId);
        this.state.count = this.rpcIds.size;
        if (this.state.count === 0) {
            browser.clearTimeout(this.startShowTimer);
            this.state.show = false;
        }
    }
}

LoadingIndicator.template = "web.LoadingIndicator";
LoadingIndicator.components = { Transition };

registry.category("main_components").add("LoadingIndicator", {
    Component: LoadingIndicator,
});
