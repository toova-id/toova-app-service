import fs from "node:fs";

const shell = fs.readFileSync(new URL("../src/app/app-shell.tsx", import.meta.url), "utf8");
const inbox = fs.readFileSync(new URL("../../managed/discuss/frontend/inbox-page.tsx", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../../managed/discuss/controllers/inbox.py", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../src/styles/globals.css", import.meta.url), "utf8");
const realtime = fs.readFileSync(new URL("../src/lib/realtime.ts", import.meta.url), "utf8");
for (const token of ["toova:inbox-counts", "inboxCounts.attention", "navigate(`${inboxAction.path}?view=", "toova-nav-badge"]) if (!shell.includes(token)) throw new Error(`inbox shell missing ${token}`);
for (const token of ["CustomEvent(\"toova:inbox-counts\"", "useSearchParams", "await refresh()", "mail.channel/new_message"] ) if (!inbox.includes(token)) throw new Error(`inbox page missing ${token}`);
if (!api.includes("'attention': messages + mentions + activities")) throw new Error("notification count must include unread messages");
if (!css.includes(".toova-nav-badge") || !css.includes("bg-destructive")) throw new Error("inbox badge must use destructive red");
for (const token of ["new WebSocket", 'event_name: "subscribe"', 'toova.bus.last', "realtimeUrl ||"]) if (!realtime.includes(token)) throw new Error(`native realtime transport missing ${token}`);
console.log("managed inbox self-check passed");
