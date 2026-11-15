import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
    testDir: "./tests/image_editor",
    testMatch: "*.spec.ts",
    outputDir: "../test-artifacts/image-editor/results",
    fullyParallel: false,
    // Keep browser/canvas memory bounded on CI hosts with many visible CPUs.
    workers: process.env.CI ? 2 : undefined,
    retries: 0,
    reporter: [
        ["list"],
        [
            "html",
            {
                outputFolder: "../test-artifacts/image-editor/report",
                open: "never",
            },
        ],
    ],
    use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://127.0.0.1:4178",
        screenshot: "only-on-failure",
        trace: "retain-on-failure",
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
            ? {
                  executablePath:
                      process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
              }
            : {},
    },
    webServer: {
        command:
            "npx vite --config tests/image_editor/vite.config.ts --host 0.0.0.0",
        url: "http://127.0.0.1:4178",
        reuseExistingServer: false,
    },
});
