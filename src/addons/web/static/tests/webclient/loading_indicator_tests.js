/** @odoo-module **/

import { browser as originalBrowser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { LoadingIndicator } from "@web/webclient/loading_indicator/loading_indicator";
import { makeTestEnv } from "../helpers/mock_env";
import {
    getFixture,
    mockTimeout,
    mount,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");

let target;

QUnit.module("LoadingIndicator", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("ui", uiService);
        patchWithCleanup(originalBrowser, {
            setTimeout: async (callback) => {
                await Promise.resolve();
                callback();
            },
        });
    },
});

QUnit.test("displays one textless spinner", async (assert) => {
    const env = await makeTestEnv();
    await mount(LoadingIndicator, target, { env });
    assert.containsNone(target, ".o_loading_indicator");

    env.bus.trigger("RPC:REQUEST", 1);
    await nextTick();

    const loadingIndicator = target.querySelector(".o_loading_indicator");
    assert.containsOnce(loadingIndicator, ".o_loading_indicator_spinner");
    assert.strictEqual(loadingIndicator.textContent.trim(), "");
    assert.strictEqual(loadingIndicator.getAttribute("role"), "status");
    assert.strictEqual(loadingIndicator.getAttribute("aria-live"), "polite");

    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    assert.containsNone(target, ".o_loading_indicator");
});

QUnit.test("keeps one spinner for concurrent RPCs", async (assert) => {
    const env = await makeTestEnv();
    await mount(LoadingIndicator, target, { env });
    env.bus.trigger("RPC:REQUEST", 1);
    env.bus.trigger("RPC:REQUEST", 2);
    await nextTick();
    assert.containsOnce(target, ".o_loading_indicator_spinner");

    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    assert.containsOnce(target, ".o_loading_indicator_spinner");

    env.bus.trigger("RPC:RESPONSE", 2);
    await nextTick();
    assert.containsNone(target, ".o_loading_indicator");
});

QUnit.test("never starts second UI blocker", async (assert) => {
    const env = await makeTestEnv();
    const { execRegisteredTimeouts } = mockTimeout();
    env.services.ui.bus.on("BLOCK", null, () => assert.step("block"));
    env.services.ui.bus.on("UNBLOCK", null, () => assert.step("unblock"));
    await mount(LoadingIndicator, target, { env });

    env.bus.trigger("RPC:REQUEST", 1);
    execRegisteredTimeouts();
    env.bus.trigger("RPC:RESPONSE", 1);

    assert.verifySteps([]);
});

QUnit.test("is not displayed immediately", async (assert) => {
    const env = await makeTestEnv();
    const { advanceTime } = mockTimeout();
    await mount(LoadingIndicator, target, { env });

    env.bus.trigger("RPC:REQUEST", 1);
    await nextTick();
    assert.containsNone(target, ".o_loading_indicator");

    await advanceTime(400);
    await nextTick();
    assert.containsOnce(target, ".o_loading_indicator_spinner");

    env.bus.trigger("RPC:RESPONSE", 1);
    await nextTick();
    assert.containsNone(target, ".o_loading_indicator");
});
