/**
 * CSRF token utilities for Django API requests.
 */

/**
 * Get CSRF token from cookie.
 * Django sets this as 'csrftoken' cookie.
 * @returns CSRF token string or empty string if not found
 */
export function getCsrfToken(): string {
    const cookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
}
