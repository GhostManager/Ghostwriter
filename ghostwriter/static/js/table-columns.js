/**
 * UI for showing/hiding table columns.
 *
 * Usage:
 * * Add this script to the page.
 * * Add the `table-column-show-hide-ui.html` snippet somewhere, set its `column_show_hide_id` value.
 * * Add `column-show-hide-table` class to the table and `data-table-name` attribute with a unique name and
 *   `data-controls-el` to the ID above.
 * * For each `th` in the first row:
 *   * Add `data-no-hide` to always show it. No other attributes are needed.
 *   * Set `data-internal-name` to a name unique to this table
 *   * If needed, set `data-name` to the name to use in the checkbox. Otherwise uses the `th`'s `textContent`.
 *   * Set `data-hide-default` boolean attribute if the column should be hidden by default.
 * * In the template, always emit all columns.
 * * Add the `show-hide-ignore` class to rows that should not have their contents altered.
 *
 */

"use strict";
document.addEventListener("DOMContentLoaded", function() {
    for(const tableEl of document.querySelectorAll(".column-show-hide-table")) {
        const uiContainer = document.getElementById(tableEl.getAttribute("data-controls-el"));

        const tableName = tableEl.getAttribute("data-table-name");
        if(tableName === null) {
            throw new Error("No column-show-hide-table or it does not have data-table-name");
        }
        const storageName = `column-show-hide-map.${tableName}`;

        /** @type {Record<string, boolean>} */
        const shownMap = JSON.parse(localStorage.getItem(storageName) ?? "{}");
        /** @type {Record<string, {input: HTMLInputElement, index_one_based: number}>} */
        const columnsMap = {};

        const updateShown = () => {
            for(const [internalName, spec] of Object.entries(columnsMap)) {
                shownMap[internalName] = spec.input.checked;
                const selector = `.column-show-hide-table tr:not(.show-hide-ignore) td:nth-child(${spec.index_one_based}), .column-show-hide-table tr:not(.show-hide-ignore) th:nth-child(${spec.index_one_based})`;
                for(const el of tableEl.querySelectorAll(selector)) {
                    el.classList.toggle("column-hide", !spec.input.checked);
                }
            }
            localStorage.setItem(storageName, JSON.stringify(shownMap));
        };

        const firstRow = tableEl.querySelector("tr");

        let n = 0;
        for(const columnTh of firstRow.querySelectorAll("th")) {
            // nth-child selector is one-based so this pre-increment gives us the correct result.
            n++;
            if(columnTh.hasAttribute("data-no-hide")) {
                continue;
            }

            const prettyName = columnTh.hasAttribute("data-name") ? columnTh.getAttribute("data-name") : columnTh.textContent;
            const internalName = columnTh.getAttribute("data-internal-name");
            if(internalName === null) {
                console.log("Header Element:", columnTh);
                throw new Error("Header element missing data-internal-name");
            }

            const node = document.createElement("div");
            node.classList.add("custom-control", "custom-checkbox", "custom-control-inline");

            const input = document.createElement("input");
            input.type = "checkbox";
            input.checked = shownMap[internalName] ?? !columnTh.hasAttribute("data-hide-default");
            input.id = `column-show-hide-checkbox-${internalName}`;
            input.classList.add("custom-control-input");
            input.addEventListener("change", updateShown);
            node.appendChild(input);

            const label = document.createElement("label");
            label.htmlFor = input.id;
            label.classList.add("custom-control-label");
            label.textContent = prettyName;
            node.appendChild(label);

            uiContainer.appendChild(node);

            columnsMap[internalName] = {
                input,
                index_one_based: n,
            };
        }

        updateShown();

        window[tableName.replaceAll("-", "_") + "_updateShownColumns"] = updateShown;
    }
});
