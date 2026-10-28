import fs from "node:fs";
import path from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

function addonFrontends(): Plugin {
  const virtualId = "virtual:addon-frontends";
  const resolvedId = `\0${virtualId}`;
  return {
    name: "addon-frontends",
    resolveId(id) { return id === virtualId ? resolvedId : undefined; },
    load(id) {
      if (id !== resolvedId) return undefined;
      const addons = path.resolve(__dirname, "../managed");
      return fs.readdirSync(addons, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(addons, entry.name, "frontend/index.ts")))
        .map((entry) => `import ${JSON.stringify(path.join(addons, entry.name, "frontend/index.ts"))};`)
        .join("\n");
    },
  };
}

export default defineConfig({
  base: "/app-assets/",
  plugins: [addonFrontends(), react()],
  resolve: {
    preserveSymlinks: true,
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@luma": path.resolve(__dirname, "src"),
      "react": path.resolve(__dirname, "node_modules/react"),
      "react/jsx-runtime": path.resolve(__dirname, "node_modules/react/jsx-runtime.js"),
      "lucide-react": path.resolve(__dirname, "node_modules/lucide-react"),
      "react-router-dom": path.resolve(__dirname, "node_modules/react-router-dom"),
    },
  },
  build: {
    outDir: "../managed/core/static/app",
    emptyOutDir: true,
    manifest: "manifest.json",
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.tsx"),
      output: {
        entryFileNames: "assets/app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8069",
      "/web": "http://127.0.0.1:8069",
    },
  },
});
