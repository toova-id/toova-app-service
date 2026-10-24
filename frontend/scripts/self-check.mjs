import { readFileSync } from "node:fs";
const manifest = JSON.parse(readFileSync(new URL("../../addons/web/static/app/manifest.json", import.meta.url)));
const entry = manifest["src/main.tsx"];
if (!entry?.isEntry || entry.file !== "assets/app.js" || !entry.css?.length) throw new Error("invalid Vite manifest");
console.log("frontend build self-check passed");
