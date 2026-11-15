import { getCsrfToken } from "../services/csrf";

type FormErrors = Record<string, string[]>;

/** Submit in place so validation errors cannot discard a staged evidence file. */
export function installEvidenceForm(form: HTMLFormElement): () => void {
    let saving = false;
    const feedback = document.createElement("div");
    feedback.className = "alert alert-danger";
    feedback.setAttribute("role", "alert");
    feedback.tabIndex = -1;
    feedback.hidden = true;
    form.prepend(feedback);
    const invalid = new Set<HTMLElement>();

    const clearErrors = () => {
        feedback.replaceChildren();
        feedback.hidden = true;
        for (const field of invalid) {
            field.classList.remove("is-invalid");
            field.removeAttribute("aria-invalid");
        }
        invalid.clear();
    };
    const showErrors = (errors: FormErrors) => {
        clearErrors();
        const title = document.createElement("p");
        title.className = "mb-1 fw-semibold";
        title.textContent = "The evidence could not be saved.";
        const list = document.createElement("ul");
        list.className = "mb-0";
        for (const [name, messages] of Object.entries(errors)) {
            const field = form.elements.namedItem(name);
            if (field instanceof HTMLElement) {
                field.classList.add("is-invalid");
                field.setAttribute("aria-invalid", "true");
                invalid.add(field);
            }
            for (const message of messages) {
                const item = document.createElement("li");
                item.textContent = message;
                list.append(item);
            }
        }
        feedback.append(title, list);
        feedback.hidden = false;
        feedback.focus();
    };

    const submit = async (event: SubmitEvent) => {
        // An open image editor's capture guard takes precedence.
        if (event.defaultPrevented) return;
        event.preventDefault();
        if (saving) return;
        saving = true;
        clearErrors();
        const body = new FormData(form);
        const controls = [...form.elements]
            .filter(
                (
                    field
                ): field is
                    | HTMLInputElement
                    | HTMLSelectElement
                    | HTMLTextAreaElement
                    | HTMLButtonElement =>
                    field instanceof HTMLInputElement ||
                    field instanceof HTMLSelectElement ||
                    field instanceof HTMLTextAreaElement ||
                    field instanceof HTMLButtonElement
            )
            .map((field) => ({ field, disabled: field.disabled }));
        const editors = [
            ...form.querySelectorAll<HTMLElement>('[contenteditable="true"]'),
        ];
        for (const { field } of controls) field.disabled = true;
        for (const editor of editors) editor.contentEditable = "false";
        form.setAttribute("aria-busy", "true");
        let navigating = false;
        try {
            const csrf =
                document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ??
                getCsrfToken();
            if (!csrf) throw new Error("CSRF token missing");
            // Django checks the multipart field before the header. A sign-in
            // in another tab can rotate the cookie while this form stays open.
            body.set("csrfmiddlewaretoken", csrf);
            const response = await fetch(form.action || location.href, {
                method: "POST",
                headers: { Accept: "application/json", "X-CSRFToken": csrf },
                body,
            });
            if (
                !response.headers
                    .get("Content-Type")
                    ?.includes("application/json")
            )
                throw new Error("Unexpected response");
            const data = await response.json();
            if (!response.ok) {
                const errors: FormErrors = {};
                if (data.errors && typeof data.errors === "object") {
                    for (const [name, values] of Object.entries(data.errors)) {
                        if (Array.isArray(values))
                            errors[name] = values.filter(
                                (value): value is string =>
                                    typeof value === "string"
                            );
                    }
                }
                if (!Object.values(errors).some((values) => values.length))
                    errors.__all__ = [
                        "Please try again. Your selected file is still available.",
                    ];
                showErrors(errors);
                return;
            }
            if (typeof data.redirect_url !== "string")
                throw new Error("Missing destination");
            const destination = new URL(data.redirect_url, location.href);
            if (destination.origin !== location.origin)
                throw new Error("Unexpected destination");
            location.assign(destination.href);
            navigating = true;
        } catch {
            showErrors({
                __all__: [
                    "Could not confirm the save. Your selected file is still available. Check your connection and try again.",
                ],
            });
        } finally {
            if (!navigating) {
                for (const { field, disabled } of controls)
                    field.disabled = disabled;
                for (const editor of editors) editor.contentEditable = "true";
                form.removeAttribute("aria-busy");
                saving = false;
            }
        }
    };
    const cancel = (event: MouseEvent) => {
        if (
            saving &&
            (event.target as Element).closest(".resource-form-actions a")
        )
            event.preventDefault();
    };
    form.addEventListener("submit", submit);
    form.addEventListener("click", cancel);
    return () => {
        form.removeEventListener("submit", submit);
        form.removeEventListener("click", cancel);
        feedback.remove();
    };
}
