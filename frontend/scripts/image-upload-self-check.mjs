import fs from "node:fs";

const registry = fs.readFileSync(new URL("../src/views/field-registry.tsx", import.meta.url), "utf8");
if (!registry.includes('editors.image = ({ value, onChange }) => <ImageUpload value={value} onChange={onChange}/>')) throw new Error("image editor must use ImageUpload");
if (registry.includes("editors.image = editors.binary")) throw new Error("generic binary editor overrides image preview");
const upload = fs.readFileSync(new URL("../src/components/ui/image-upload.tsx", import.meta.url), "utf8");
for (const token of ["toova-image-preview", "imageSource(value)", "Unggah gambar", "Ganti gambar", "Hapus gambar"]) if (!upload.includes(token)) throw new Error(`image upload missing ${token}`);
const css = fs.readFileSync(new URL("../src/styles/globals.css", import.meta.url), "utf8");
const rules = Object.fromEntries(css.split("\n").filter((line) => line.trim().startsWith(".")).map((line) => [line.split("{", 1)[0].trim(), line]));
for (const selector of [".toova-image-upload", ".workspace-image-value"]) {
  if (!rules[selector]?.includes("--image-upload-size:")) throw new Error(`${selector} must define --image-upload-size token`);
}
for (const [selector, rule] of Object.entries(rules)) {
  if (!/toova-image-(upload|empty|preview)|workspace-image-value/.test(selector)) continue;
  if (/\baspect-/.test(rule)) throw new Error(`image upload must use fixed size, not aspect ratio: ${selector}`);
}
for (const selector of [".toova-image-empty", ".toova-image-preview"]) {
  if (!rules[selector]?.includes("h-[var(--image-upload-size)]")) throw new Error(`${selector} must be sized by --image-upload-size`);
}
console.log("image upload self-check passed");
