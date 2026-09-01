import { defineConfig } from "vite";

export default defineConfig({
    build: {
        emptyOutDir: true,
        minify: false,
        outDir: "dist_html_compatibility",
        rollupOptions: {
            input: "./src/tiptap_gw/html_compatibility.test.ts",
            output: {
                entryFileNames: "compatibility-test.js",
            },
        },
        ssr: true,
    },
});
