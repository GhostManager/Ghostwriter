(function () {
    'use strict';

    const CONFIG_ELEMENT_ID = 'gw-current-date';
    const RETRY_DELAY_MS = 60 * 1000;
    const STOP_REFRESH = {};
    let activated = false;
    let clockOffsetMs = 0;
    let refreshPromise = null;
    let refreshTimeoutId = null;

    function isValidConfig(config) {
        return Boolean(
            config &&
            typeof config === 'object' &&
            typeof config.date === 'string' &&
            config.date.length > 0 &&
            Number.isFinite(config.expiresAt) &&
            Number.isFinite(config.serverTime) &&
            typeof config.refreshUrl === 'string' &&
            config.refreshUrl.length > 0
        );
    }

    function isFreshConfig(config) {
        return isValidConfig(config) && config.expiresAt > config.serverTime;
    }

    function readConfig() {
        const configElement = document.getElementById(CONFIG_ELEMENT_ID);
        if (!configElement || !configElement.textContent) {
            return null;
        }

        try {
            const config = JSON.parse(configElement.textContent);
            return isValidConfig(config) ? config : null;
        } catch (error) {
            return null;
        }
    }

    function serverNow() {
        return Date.now() + clockOffsetMs;
    }

    function setConfig(config) {
        const configElement = document.getElementById(CONFIG_ELEMENT_ID);
        if (!configElement || !isValidConfig(config)) {
            return false;
        }

        configElement.textContent = JSON.stringify(config);
        clockOffsetMs = config.serverTime - Date.now();
        return true;
    }

    const initialConfig = readConfig();
    if (initialConfig) {
        clockOffsetMs = initialConfig.serverTime - Date.now();
    }

    function scheduleRefresh(config) {
        if (!isValidConfig(config)) {
            return false;
        }
        if (refreshTimeoutId !== null) {
            window.clearTimeout(refreshTimeoutId);
        }

        const delay = Math.max(config.expiresAt - serverNow() + 250, 0);
        refreshTimeoutId = window.setTimeout(refreshCurrentDate, delay);
        return true;
    }

    function scheduleRetry() {
        if (refreshTimeoutId !== null) {
            window.clearTimeout(refreshTimeoutId);
        }
        refreshTimeoutId = window.setTimeout(refreshCurrentDate, RETRY_DELAY_MS);
    }

    function stopRefreshing() {
        if (refreshTimeoutId !== null) {
            window.clearTimeout(refreshTimeoutId);
            refreshTimeoutId = null;
        }
        activated = false;
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
            if (response.redirected || response.status === 401 || response.status === 403) {
                stopRefreshing();
                return STOP_REFRESH;
            }
            if (!response.ok) {
                throw new Error(`Date shortcut refresh failed with status ${response.status}`);
            }
            return response.json();
        }).then(function (newConfig) {
            if (newConfig === STOP_REFRESH) {
                return false;
            }
            if (!isFreshConfig(newConfig)) {
                throw new Error('Date shortcut refresh returned an invalid configuration');
            }
            if (!setConfig(newConfig)) {
                return false;
            }
            return scheduleRefresh(newConfig);
        }).catch(function () {
            scheduleRetry();
            return false;
        }).finally(function () {
            refreshPromise = null;
        });

        return refreshPromise;
    }

    function currentDate() {
        activate();
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

    function resolveCurrentDate() {
        const date = currentDate();
        if (date) {
            return Promise.resolve(date);
        }

        return refreshCurrentDate().then(function (refreshed) {
            const config = readConfig();
            if (!refreshed || !config || serverNow() >= config.expiresAt) {
                return '';
            }
            return config.date;
        });
    }

    function activate() {
        if (activated) {
            return true;
        }

        const config = readConfig();
        if (!config) {
            return false;
        }

        activated = true;
        scheduleRefresh(config);
        return true;
    }

    window.GW_EDITOR_SHORTCUTS = Object.freeze({
        activate: activate,
        currentDate: currentDate,
        refreshCurrentDate: refreshCurrentDate,
        resolveCurrentDate: resolveCurrentDate,
    });
})();
