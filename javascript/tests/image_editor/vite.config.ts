import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const repository = fileURLToPath(new URL("../../../", import.meta.url));

export default defineConfig({
    root,
    plugins: [
        react(),
        {
            name: "ghostwriter-static-fixture",
            configureServer(server) {
                server.middlewares.use((request, _response, next) => {
                    if (request.url?.startsWith("/static/"))
                        request.url = request.url.slice(7);
                    next();
                });
            },
        },
    ],
    publicDir: repository + "ghostwriter/static",
    server: { port: 4178, strictPort: true, fs: { allow: [repository] } },
});
