/**
 * CSRF token utilities for Django API requests.
 */

/**
 * Get CSRF token from the server-rendered DOM.
 * Prefer the collab meta tag and fall back to Django's hidden form input.
 * @returns CSRF token string or empty string if not found
 */
export function getCsrfToken(): string {
    const metaToken = document.querySelector<HTMLMetaElement>(
        'meta[name="csrf-token"]'
    )?.content;
    if (metaToken) {
        return metaToken;
    }

    const formToken = document.querySelector<HTMLInputElement>(
        'input[name="csrfmiddlewaretoken"]'
    )?.value;
    return formToken ?? "";
}
