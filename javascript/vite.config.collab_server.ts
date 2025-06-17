import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    return {
        plugins: [react()],
        build: {
            ssr: resolve(__dirname, "./src/collab_server/index.ts"),
            outDir: "dist_collab_server",
            sourcemap: mode === "development",
            target: "es2022",
        },
    };
});
