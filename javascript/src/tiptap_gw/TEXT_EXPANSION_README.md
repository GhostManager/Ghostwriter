# Text Expansion Feature

## Overview

Keyboard-driven acronym expansion for cybersecurity professionals. Press `Ctrl+Space` (or `Cmd+Space` on Mac) to expand acronyms inline.

## Usage

1. Type an acronym (e.g., `XSS`, `csrf`, `API`)
2. Press `Ctrl+E` (Windows) `CMD+E` (Mac)
3. **Single match:** Text expands immediately
4. **Multiple matches:** Modal appears with options

## Features

- ✅ Case-insensitive matching (`xss` = `XSS` = `Xss`)
- ✅ 50+ security and technology acronyms pre-loaded
- ✅ Keyboard-friendly modal navigation (Arrow keys, Enter, Escape)
- ✅ Non-intrusive (only activates on shortcut)

## Examples

```
Type: XSS
Press: Ctrl+Space
Result: Cross-Site Scripting

Type: CIA
Press: Ctrl+Space
Result: Modal shows:
  ○ Central Intelligence Agency (government)
  ○ Confidentiality, Integrity, and Availability (security)
```

## Adding New Acronyms

Edit `ghostwriter/modules/acronyms/acronyms.yml`:

```yaml
NEWACRO:
  - full: "Full Expansion Text"
    category: "security"
```

Rebuild frontend:
```bash
cd javascript && npm run build-frontend-prod
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` / `Cmd+Space` | Expand acronym at cursor |
| `Arrow Up/Down` | Navigate options (in modal) |
| `Enter` | Select option |
| `Escape` | Cancel expansion |

## Technical Details

**Architecture:**
- Backend: YAML data file (`ghostwriter/modules/acronyms/acronyms.yml`)
- Frontend: TipTap extension (`text_expansion.ts`) + React modal
- Bundling: YAML loaded as static asset via `@rollup/plugin-yaml`

**Files:**
- [`ghostwriter/modules/acronyms/acronyms.yml`](../../../ghostwriter/modules/acronyms/acronyms.yml) - Acronym definitions
- [`javascript/src/tiptap_gw/text_expansion.ts`](text_expansion.ts) - TipTap extension
- [`javascript/src/frontend/collab_forms/rich_text_editor/text_expansion_modal.tsx`](../../frontend/collab_forms/rich_text_editor/text_expansion_modal.tsx) - Disambiguation modal

**Performance:**
- Lookup: O(1) hash map
- Bundle size: ~5KB for YAML data
- No network requests

## Troubleshooting

**Shortcut not working:**
- Check browser/OS doesn't intercept `Ctrl+Space`
- Try clicking in editor first (ensure focus)

**Acronym not expanding:**
- Verify acronym exists in `acronyms.yml`
- Check case (should be case-insensitive)
- Ensure cursor is immediately after acronym

**After adding acronyms:**
- Rebuild frontend: `npm run build-frontend-prod`
- Restart Django containers if needed
