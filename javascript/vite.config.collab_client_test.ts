import { defineConfig } from "vite";

export default defineConfig({
    build: {
        emptyOutDir: true,
        minify: false,
        outDir: "dist_collab_client_test",
        rollupOptions: {
            input: "./src/collab_server/graphql_client.test.ts",
            output: {
                entryFileNames: "graphql-client-test.js",
            },
        },
        ssr: true,
    },
    ssr: {
        noExternal: true,
    },
});
