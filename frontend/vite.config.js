import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  // One file (HTML with the CSS and JS inside): the browser loads the page in a single request,
  // so one warm Lambda copy is enough. Parallel requests would each cold-start a new copy.
  plugins: [react(), viteSingleFile()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
