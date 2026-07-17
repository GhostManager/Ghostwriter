# TinyMCE Skin Notes

This directory contains the TinyMCE skins bundled with Ghostwriter.

## TinyMCE version

The checked-in TinyMCE runtime is `5.10.8`.

You can verify that in [`tinymce.min.js`](../tinymce.min.js), which exposes:

- `majorVersion: "5"`
- `minorVersion: "10.8"`
- `releaseDate: "2023-10-19"`

## What is source vs generated

There are two different kinds of assets here:

- Upstream TinyMCE skins copied from the TinyMCE distribution.
- Ghostwriter-specific skins that customize TinyMCE to match the project UI.

Current layout:

- [`skintool.json`](./skintool.json)
  Build input for the original `Ghostwriter` skin.
- [`ui/Ghostwriter`](./ui/Ghostwriter)
  Readable source files are checked in alongside minified outputs:
  `skin.css`, `skin.mobile.css`, `content.css`, `content.inline.css`, `content.mobile.css`
  plus the corresponding `.min.css` files.
- [`content/Ghostwriter`](./content/Ghostwriter)
  Readable `content.css` plus `content.min.css`.
- [`ui/GhostwriterDark`](./ui/GhostwriterDark)
  Currently committed as compiled/minified outputs only.
- [`content/GhostwriterDark`](./content/GhostwriterDark)
  Currently committed as compiled/minified outputs only.

## Provenance

- `Ghostwriter` was created with Tiny's skin tooling and is represented by [`skintool.json`](./skintool.json).
- `GhostwriterDark` was introduced later to make TinyMCE match Ghostwriter's dark mode more closely than TinyMCE's default `oxide-dark` skin.
- Some dark-skin tweaks are therefore project-owned customizations on top of TinyMCE-provided assets.

## Regeneration guidance

When updating TinyMCE or changing the project-owned skins:

1. Start from the matching TinyMCE release bundled in `ghostwriter/static/js/tinymce/`.
2. Treat upstream `oxide` / `oxide-dark` skin files as the baseline reference for that TinyMCE version.
3. Keep any editable/source files in the repo whenever possible.
   For `Ghostwriter`, update the readable CSS and regenerate the minified outputs.
4. If `GhostwriterDark` is rebuilt, commit both:
   - the generated `.min.css` assets TinyMCE actually loads, and
   - the readable source or build inputs used to create them.
5. If a future change is a one-off manual patch to a generated file, document it here or in the changelog so the next TinyMCE upgrade knows what to preserve.

## Maintenance notes

- TinyMCE loads the minified files in production, so those outputs must stay committed.
- [`config.js`](../config.js) selects the active skin and content CSS at runtime.
- [`wysiwyg_styles.css`](../../../css/wysiwyg_styles.css) still provides Ghostwriter-specific editor content styling on top of TinyMCE's content skin.

## Recommended future cleanup

The best long-term follow-up is to add readable source files for `GhostwriterDark` next to the current minified outputs, so future diffs do not have to happen against minified CSS alone.
