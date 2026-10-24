import fs from "node:fs";

const registry = fs.readFileSync(new URL("../src/views/field-registry.tsx", import.meta.url), "utf8");
if (!registry.includes('editors.image = ({ value, onChange }) => <ImageUpload value={value} onChange={onChange}/>')) throw new Error("image editor must use ImageUpload");
if (registry.includes("editors.image = editors.binary")) throw new Error("generic binary editor overrides image preview");
const upload = fs.readFileSync(new URL("../src/components/ui/image-upload.tsx", import.meta.url), "utf8");
for (const token of ["luma-image-preview", "imageSource(value)", "Unggah gambar", "Ganti gambar", "Hapus gambar"]) if (!upload.includes(token)) throw new Error(`image upload missing ${token}`);
console.log("image upload self-check passed");
