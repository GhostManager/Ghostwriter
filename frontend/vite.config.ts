import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
    //console.log(mode, process.env);
    return {
        plugins: [react()],
        build: {
            rollupOptions: {
                input: {
                    "cvss": resolve(__dirname, "./src/cvss/ui.js"),
                },
                output: {
                    entryFileNames: "assets/[name].js",
                    //chunkFileNames: "assets/[name].js",
                    assetFileNames: "assets/[name].[ext]",
                },
            },
            sourcemap: mode === "development",
            watch: mode === "development" ? {
                chokidar: {
                    // Needed for docker on WSL
                    usePolling: true,
                },
            } : null,
        }
    };
});
