import { ImageIcon, Maximize2, Trash2, Upload } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const maxBytes = 10 * 1024 * 1024;

export function imageSource(value: unknown): string | undefined {
  if (typeof value !== "string" || !value) return undefined;
  if (value.startsWith("data:image/")) return value;
  const prefix = value.slice(0, 12);
  const mime = prefix.startsWith("/9j/") ? "image/jpeg" : prefix.startsWith("iVBOR") ? "image/png" : prefix.startsWith("R0lGOD") ? "image/gif" : prefix.startsWith("UklGR") ? "image/webp" : "image/png";
  return `data:${mime};base64,${value}`;
}

export function ImageUpload({ value, onChange, disabled, className }: { value: unknown; onChange: (value: string | false) => void; disabled?: boolean; className?: string }) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string>();
  const source = imageSource(value);

  function load(file?: File) {
    if (!file) return;
    if (!allowedTypes.has(file.type)) return setError("Gunakan JPG, PNG, WebP, atau GIF.");
    if (file.size > maxBytes) return setError("Ukuran gambar maksimal 10 MB.");
    const reader = new FileReader();
    reader.onerror = () => setError("Gambar gagal dibaca.");
    reader.onload = () => { setError(undefined); onChange(String(reader.result).split(",", 2)[1] || false); };
    reader.readAsDataURL(file);
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (!disabled) load(event.dataTransfer.files[0]);
  }

  return <div className={cn("luma-image-upload", dragging && "is-dragging", className)} onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={drop}>
    <input ref={input} id={id} type="file" className="sr-only" accept="image/jpeg,image/png,image/webp,image/gif" disabled={disabled} onChange={(event) => { load(event.target.files?.[0]); event.target.value = ""; }}/>
    {source ? <div className="luma-image-preview"><img src={source} alt="Pratinjau gambar"/><div><Button type="button" variant="ghost" size="icon" onClick={() => input.current?.click()} disabled={disabled} aria-label="Ganti gambar"><Upload/></Button><Button asChild type="button" variant="ghost" size="icon"><a href={source} target="_blank" rel="noreferrer" aria-label="Lihat ukuran penuh"><Maximize2/></a></Button><Button type="button" variant="ghost" size="icon" className="text-destructive" onClick={() => { setError(undefined); onChange(false); }} disabled={disabled} aria-label="Hapus gambar"><Trash2/></Button></div></div> : <button type="button" className="luma-image-empty" onClick={() => input.current?.click()} disabled={disabled}><ImageIcon/><strong>Unggah gambar</strong><small>JPG, PNG, WebP, GIF · maks. 10 MB</small></button>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
