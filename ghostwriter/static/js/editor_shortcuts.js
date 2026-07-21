(function () {
    'use strict';

    const CONFIG_ELEMENT_ID = 'gw-current-date';
    const RETRY_DELAY_MS = 60 * 1000;
    let clockOffsetMs = 0;
    let refreshPromise = null;
    let refreshTimeoutId = null;

    function readConfig() {
        const configElement = document.getElementById(CONFIG_ELEMENT_ID);
        if (!configElement || !configElement.textContent) {
            return null;
        }

        try {
            const config = JSON.parse(configElement.textContent);
            if (
                typeof config.date !== 'string' ||
                !Number.isFinite(config.expiresAt) ||
                !Number.isFinite(config.serverTime) ||
                typeof config.refreshUrl !== 'string'
            ) {
                return null;
            }
            return config;
        } catch (error) {
            return null;
        }
    }

    function serverNow() {
        return Date.now() + clockOffsetMs;
    }

    function setConfig(config) {
        const configElement = document.getElementById(CONFIG_ELEMENT_ID);
        if (!configElement) {
            return false;
        }

        configElement.textContent = JSON.stringify(config);
        clockOffsetMs = config.serverTime - Date.now();
        return true;
    }

    function scheduleRefresh(config) {
        if (refreshTimeoutId !== null) {
            window.clearTimeout(refreshTimeoutId);
        }

        const delay = Math.max(config.expiresAt - serverNow() + 250, 0);
        refreshTimeoutId = window.setTimeout(refreshCurrentDate, delay);
    }

    function scheduleRetry() {
        if (refreshTimeoutId !== null) {
            window.clearTimeout(refreshTimeoutId);
        }
        refreshTimeoutId = window.setTimeout(refreshCurrentDate, RETRY_DELAY_MS);
    }

    function refreshCurrentDate() {
        if (refreshPromise) {
            return refreshPromise;
        }

        const config = readConfig();
        if (!config) {
            return Promise.resolve(false);
        }

        refreshPromise = window.fetch(config.refreshUrl, {
            cache: 'no-store',
            credentials: 'same-origin',
            headers: {Accept: 'application/json'},
        }).then(function (response) {
            if (!response.ok) {
                throw new Error(`Date shortcut refresh failed with status ${response.status}`);
            }
            return response.json();
        }).then(function (newConfig) {
            if (!setConfig(newConfig)) {
                return false;
            }
            scheduleRefresh(newConfig);
            return true;
        }).catch(function () {
            scheduleRetry();
            return false;
        }).finally(function () {
            refreshPromise = null;
        });

        return refreshPromise;
    }

    function currentDate() {
        const config = readConfig();
        if (!config) {
            return '';
        }
        if (serverNow() >= config.expiresAt) {
            refreshCurrentDate();
            return '';
        }
        return config.date;
    }

    window.GW_EDITOR_SHORTCUTS = Object.freeze({
        currentDate: currentDate,
        refreshCurrentDate: refreshCurrentDate,
    });

    const initialConfig = readConfig();
    if (initialConfig) {
        setConfig(initialConfig);
        scheduleRefresh(initialConfig);
    }
})();
