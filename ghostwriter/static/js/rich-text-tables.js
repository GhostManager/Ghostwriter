(() => {
    function initRichTextTables(root = document) {
        root.querySelectorAll("[data-rich-text-tables] table").forEach((table, index) => {
            if (table.parentElement.classList.contains("table-responsive")) return;

            const wrapper = document.createElement("div");
            wrapper.className = "table-responsive rich-text-table";
            wrapper.tabIndex = 0;
            wrapper.setAttribute("role", "region");
            wrapper.setAttribute("aria-label", table.caption?.textContent.trim() || `Rich text table ${index + 1}`);
            table.before(wrapper);
            wrapper.append(table);
        });
    }

    window.gwInitRichTextTables = initRichTextTables;
    initRichTextTables();
})();
