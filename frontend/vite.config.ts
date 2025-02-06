import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    //console.log(mode, process.env);
    return {
        plugins: [react()],
        build: {
            rollupOptions: {
                input: {
                    cvss: resolve(__dirname, "./src/cvss/ui.js"),
                    collab_forms_observation: resolve(
                        __dirname,
                        "./src/collab_forms/forms/observation.html"
                    ),
                },
                output: {
                    entryFileNames: "assets/[name].js",
                    chunkFileNames: "assets/[name].js",
                    assetFileNames: "assets/[name].[ext]",
                    manualChunks(id) {
                        if (id.includes("node_modules")) return "vendor";
                        if (
                            id.includes("/collab_forms/") &&
                            !id.includes("/collab_forms/forms/")
                        )
                            return "collab_common";
                    },
                },
            },
            sourcemap: mode === "development",
            watch:
                mode === "development"
                    ? {
                          chokidar: {
                              // Needed for docker on WSL
                              usePolling: true,
                          },
                      }
                    : null,
        },
    };
});
