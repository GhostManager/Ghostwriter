const REFRESH_WINDOW_MS = 5 * 60 * 1000;
const REFRESH_RETRY_MS = 30 * 1000;
const REFRESH_TIMEOUT_MS = 15 * 1000;
const MAX_TIMER_MS = 2_147_483_647;

type CollabTokenEvent = "refreshed" | "expired";
type CollabTokenListener = (event: CollabTokenEvent) => void;

class CollabTokenRefreshError extends Error {
    constructor(
        message: string,
        readonly terminal: boolean
    ) {
        super(message);
        this.name = "CollabTokenRefreshError";
    }
}

let currentToken: string | null = null;
let expiresAtMs = 0;
let initialized = false;
let refreshPromise: Promise<string> | null = null;
let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let nextRefreshAttemptAt = 0;
const listeners = new Set<CollabTokenListener>();

function requiredElementText(id: string): string {
    const value = document.getElementById(id)?.textContent?.trim();
    if (!value) {
        throw new Error(`Missing collaboration setting: ${id}`);
    }
    return value;
}

function tokenExpiration(token: string): number {
    try {
        const encodedPayload = token.split(".")[1];
        const padding = "=".repeat((4 - (encodedPayload.length % 4)) % 4);
        const payload = JSON.parse(
            atob(encodedPayload.replace(/-/g, "+").replace(/_/g, "/") + padding)
        );
        if (typeof payload.exp === "number") {
            return payload.exp * 1000;
        }
    } catch {
        // The server will authoritatively validate the token. This parsing is
        // only used to schedule renewal in the browser.
    }
    throw new Error("Collaboration token has no valid expiration");
}

function initialize() {
    if (initialized) return;
    currentToken = requiredElementText("yjs-jwt");
    expiresAtMs = tokenExpiration(currentToken);
    initialized = true;
    scheduleRefresh();
}

function notify(event: CollabTokenEvent) {
    listeners.forEach((listener) => listener(event));
}

function expireToken() {
    if (currentToken === null) return;
    currentToken = null;
    if (refreshTimer !== null) clearTimeout(refreshTimer);
    refreshTimer = null;
    notify("expired");
}

function handleRefreshFailure(error: unknown) {
    if (error instanceof CollabTokenRefreshError && error.terminal) {
        expireToken();
        return;
    }

    const remainingMs = expiresAtMs - Date.now();
    if (remainingMs <= 0) {
        expireToken();
        return;
    }
    const retryDelay = Math.min(REFRESH_RETRY_MS, remainingMs);
    nextRefreshAttemptAt = Date.now() + retryDelay;
    scheduleRefresh(retryDelay);
}

function scheduleRefresh(delayOverride?: number) {
    if (currentToken === null) return;
    if (refreshTimer !== null) clearTimeout(refreshTimer);

    const remainingMs = expiresAtMs - Date.now();
    if (remainingMs <= 0) {
        expireToken();
        return;
    }

    const delay = delayOverride ?? Math.max(0, remainingMs - REFRESH_WINDOW_MS);
    refreshTimer = setTimeout(
        () => {
            refreshTimer = null;
            void refreshCollabToken().catch(handleRefreshFailure);
        },
        Math.min(delay, MAX_TIMER_MS)
    );
}

async function requestCollabToken(): Promise<string> {
    const csrfToken = document.querySelector<HTMLMetaElement>(
        'meta[name="csrf-token"]'
    )?.content;
    if (!csrfToken) {
        throw new CollabTokenRefreshError(
            "Missing collaboration CSRF token",
            true
        );
    }

    const abortController = new AbortController();
    const timeout = setTimeout(
        () => abortController.abort(),
        REFRESH_TIMEOUT_MS
    );
    let response: Response;
    let data: unknown;
    try {
        response = await fetch(
            requiredElementText("collab-token-refresh-url"),
            {
                method: "POST",
                credentials: "same-origin",
                signal: abortController.signal,
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({
                    model: requiredElementText("yjs-model"),
                    id: requiredElementText("yjs-object-id"),
                }),
            }
        );

        if (response.ok) data = await response.json();
    } finally {
        clearTimeout(timeout);
    }

    if (!response.ok) {
        throw new CollabTokenRefreshError(
            `Collaboration token renewal failed (${response.status})`,
            response.status >= 400 &&
                response.status < 500 &&
                response.status !== 408 &&
                response.status !== 429
        );
    }

    if (
        typeof data !== "object" ||
        data === null ||
        typeof (data as { token?: unknown }).token !== "string" ||
        typeof (data as { expiresAt?: unknown }).expiresAt !== "number"
    ) {
        throw new CollabTokenRefreshError(
            "Collaboration token renewal returned invalid data",
            false
        );
    }

    const token = (data as { token: string }).token;
    const responseExpiration = (data as { expiresAt: number }).expiresAt * 1000;
    const parsedExpiration = tokenExpiration(token);
    if (
        responseExpiration <= Date.now() ||
        Math.abs(responseExpiration - parsedExpiration) > 1000
    ) {
        throw new CollabTokenRefreshError(
            "Collaboration token renewal returned an invalid expiration",
            false
        );
    }

    currentToken = token;
    expiresAtMs = responseExpiration;
    nextRefreshAttemptAt = 0;
    scheduleRefresh();
    notify("refreshed");
    return token;
}

async function refreshCollabToken(): Promise<string> {
    initialize();
    if (refreshPromise !== null) return refreshPromise;

    const request = requestCollabToken();
    refreshPromise = request;
    try {
        return await request;
    } finally {
        if (refreshPromise === request) refreshPromise = null;
    }
}

export async function getCollabToken(): Promise<string> {
    initialize();
    if (currentToken === null) {
        throw new Error("Collaboration authentication expired");
    }

    if (
        expiresAtMs - Date.now() <= REFRESH_WINDOW_MS &&
        Date.now() >= nextRefreshAttemptAt
    ) {
        try {
            return await refreshCollabToken();
        } catch (error) {
            handleRefreshFailure(error);
            if (currentToken === null) throw error;
        }
    }
    return currentToken;
}

export function subscribeCollabToken(listener: CollabTokenListener) {
    initialize();
    listeners.add(listener);
    return () => listeners.delete(listener);
}
