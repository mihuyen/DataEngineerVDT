import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Group by package name (not a static entry-point array) so every
        // module recharts/lucide-react/radix-ui pull in transitively lands
        // in the same named vendor chunk, instead of Rollup picking an
        // arbitrary app-code module name for whatever shared chunk those
        // dependencies end up hoisted into.
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("recharts") || id.includes("d3-")) return "vendor-charts";
          if (id.includes("lucide-react")) return "vendor-icons";
          if (id.includes("@radix-ui")) return "vendor-radix";
          return "vendor";
        },
      },
    },
  },
});
