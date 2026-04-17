/**
 * CSRF token utilities for Django API requests.
 */

/**
 * Get CSRF token from the server-rendered DOM.
 * @returns CSRF token string or empty string if not found
 */
export function getCsrfToken(): string {
    const token = document.querySelector<HTMLMetaElement>(
        'meta[name="csrf-token"]'
    )?.content;
    return token ?? "";
}
