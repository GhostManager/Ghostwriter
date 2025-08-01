-   Ensure that the all model fields exposed to collaborative editing allow blank values, are not unique, and do not have model-level validation (or if they do, that it is replicated in the form and will not be sent to the collab server).
-   Add an entry in `/ghostwriter/api/views.py` `CheckEditPermissions` `available_models`.
    -   Ensure your model has a `user_can_edit` method, that takes a user as an argument and returns a boolean.
-   Create a form `/frontend/src/collab_forms/forms/`, and add its file to `vite.config.ts` `build.rollupOptions.input`, with the bundle name `collab_forms_<modelname>` replacing `<modelname>` with the lowercased no-separators Django model name (ex. `reportfindinglink`).
-   Subclass `/ghostwriter/commandcenter/views.py` `CollabModelUpdate` and set the appropriate class attributes
    -   Extend the `collab_editing/update.html` template with breadcrumbs, etc. for the model and set the `template_name` class attribute.
-   Add a handler in `/collab-server/src/handlers` and set it up in `HANDLERS` in `collab-server/src/index.ts`.
    -   If needed, ensure the models' tags field is named `tags` and add the model to `/ghostwriter/api/views.py` `GetTags` / `SetTags` to use the graphql `tags` / `setTags` endpoints.
-   Avoid duplicating forms. Ensure that "create" views for the model either: do not have a form or any GET functionality, and create their models with default values on POST and redirect to the collab edit page; or that the form for a new model asks for necessary, non-collab-editable fields only.
