import fs from "node:fs";

// Relation drawers render inside a <label className="managed-form-field">. Without a portal the
// nested-label markup forwards stray clicks to the drawer buttons and the draft resets.
const roots = [new URL("../src/", import.meta.url), new URL("../../managed/", import.meta.url)];
const files = roots.flatMap((root) => fs.readdirSync(root, { recursive: true, encoding: "utf8" }).filter((name) => name.endsWith(".tsx")).map((name) => new URL(name, root)));
let checked = 0;
for (const file of files) {
  const source = fs.readFileSync(file, "utf8");
  if (!source.includes("managed-relation-editor-backdrop")) continue;
  checked += 1;
  if (!source.includes('createPortal(<div className="managed-relation-editor-backdrop"') || !source.includes("document.body)"))
    throw new Error(`${file.pathname} must render managed-relation-editor-backdrop through createPortal(..., document.body)`);
}
if (checked < 6) throw new Error(`expected at least 6 relation drawers, found ${checked}`);
console.log(`relation drawer self-check passed (${checked} drawers)`);
