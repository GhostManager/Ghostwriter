(function () {
    const button = document.getElementById("scroll-button");
    if (!button) {
        return;
    }

    function updateVisibility() {
        button.hidden = window.scrollY <= 300;
    }

    window.addEventListener("scroll", updateVisibility, { passive: true });
    window.addEventListener("resize", updateVisibility);
    window.addEventListener("pageshow", updateVisibility);
    button.addEventListener("click", function () {
        const reducedMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;
        window.scrollTo({ top: 0, behavior: reducedMotion ? "auto" : "smooth" });
    });

    updateVisibility();
})();
