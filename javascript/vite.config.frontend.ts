import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    return {
        base: "./",
        plugins: [react()],
        build: {
            rollupOptions: {
                input: {
                    collab_forms_observation:
                        "./src/frontend/collab_forms/forms/observation.tsx",
                    collab_forms_reportobservationlink:
                        "./src/frontend/collab_forms/forms/reportobservationlink.tsx",
                    collab_forms_finding:
                        "./src/frontend/collab_forms/forms/finding.tsx",
                    collab_forms_reportfindinglink:
                        "./src/frontend/collab_forms/forms/reportfindinglink.tsx",
                    collab_forms_report_field:
                        "./src/frontend/collab_forms/forms/report_field.tsx",
                    collab_forms_project_collabnote:
                        "./src/frontend/collab_forms/forms/project_collabnote.tsx",
                    admin_tiptap: "./src/frontend/admin_tiptap.tsx",
                    standalone_tiptap: "./src/frontend/standalone_tiptap.tsx",
                    standalone_tiptap_loader:
                        "./src/frontend/standalone_tiptap_loader.ts",
                },
                output: {
                    entryFileNames: "assets/[name].js",
                    // Templates reference stable entry names. Content-hash shared
                    // chunks so a refreshed entry never reuses an incompatible
                    // cached collaboration runtime after an upgrade.
                    chunkFileNames: "assets/[name]-[hash].js",
                    assetFileNames: "assets/[name].[ext]",
                    manualChunks(id) {
                        if (id.includes("node_modules")) return "vendor";
                        if (
                            id.includes("/frontend/collab_forms/") &&
                            !id.includes("/frontend/collab_forms/forms/")
                        )
                            return "collab_common";
                    },
                },
            },
            outDir: "dist_frontend",
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
