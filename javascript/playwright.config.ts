import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.GW_BASE_URL ?? "http://localhost:8000";

export default defineConfig({
    testDir: "./tests/e2e",
    outputDir: "../test-artifacts/playwright/results",
    fullyParallel: false,
    retries: 0,
    reporter: [["list"], ["html", { outputFolder: "../test-artifacts/playwright/html-report", open: "never" }]],
    use: {
        baseURL,
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
        video: "on",
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
});
