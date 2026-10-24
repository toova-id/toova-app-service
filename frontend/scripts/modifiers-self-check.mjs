import { evaluateDomain } from "../src/views/modifiers.ts";

const started = performance.now();
assert(evaluateDomain(["|", ["is_company", "=", true], ["name", "=", false]], { is_company: true }), "OR true branch");
assert(!evaluateDomain(["|", ["is_company", "=", true], ["name", "=", false]], { is_company: false, name: "Ada" }), "OR false branches");
assert(evaluateDomain(["&", ["active", "=", true], ["country", "=", "ID"]], { active: true, country: "ID" }), "AND branches");
assert(performance.now() - started < 100, "modifier evaluation must terminate");
console.log("modifier self-check passed");

function assert(value, message) {
  if (!value) throw new Error(message);
}
