# Scribe — MVP Todo

Build order. Each phase ends with something runnable/testable. See `design-doc.md` for the spec.

## Phase 0 — Skeleton
- [x] 1. Python project (`pyproject.toml`, Textual), `scribe` entry point.
- [x] 2. Config: notes directory via CLI arg or config file; create if missing.
- [x] 3. pytest setup — parser/serializer tests are the priority.

## Phase 1 — Markdown ↔ block tree (no UI)
- [x] 4. Block model: ephemeral UUID, text (multi-line), children, parent, properties, task state.
- [x] 5. Parser: `.md` → block tree. Handles `- ` bullets + indentation (tabs or 2-space), multi-line blocks, fenced code blocks inside blocks, `key:: value` properties, `TODO`/`DOING`/`DONE` markers, page-level properties at top of file.
- [x] 6. Serializer: block tree → `.md`.
- [x] 7. Round-trip tests: parse → serialize == original for all the above. (Data-safety tests; do before any UI.)
- [x] 8. Link extraction: `[[page]]`, `#tag`, `#[[multi word tag]]` per block (ignore inside code blocks).
- [x] 9. Page name ↔ filename mapping (escape `/` etc.); journal naming `YYYY_MM_DD.md`.

## Phase 2 — SQLite index
- [ ] 10. Schema: `pages`, `blocks` (id, page, parent, order, text), `refs` (block_id → target page).
- [ ] 11. Full rebuild on startup from all `.md` files (in-memory or temp DB).
- [ ] 12. Queries: backlinks for a page, list all pages.
- [ ] 13. Re-index a single page on save/reload so backlinks stay current within a session.

## Phase 3 — Page view (read-only)
- [x] 14. Textual app shell; launches on today's journal (create if missing).
- [x] 15. Outline widget: render bullets, indentation, block cursor (`j`/`k` by default; rebindable in `keybinds.yaml`).
- [ ] 16. Render: task-state styling, properties (dimmed), link highlighting, code blocks w/ syntax highlighting.
- [ ] 17. Backlinks panel below the page (blocks referencing this page, grouped by source page).

## Phase 4 — Editing
- [ ] 18. Modal: normal mode moves between blocks; `i`/Enter edits current block in a `TextArea`; `Esc` commits.
- [ ] 19. Block ops: new sibling below/above (`o`/`O`), indent/outdent (`Tab`/`Shift-Tab`), delete, move up/down.
- [ ] 20. Multi-line editing within a block (newline key that doesn't commit).
- [ ] 21. Cycle task state key (none → TODO → DOING → DONE).
- [ ] 22. Keybinding audit: nothing on `Ctrl-W` or other Vim `:terminal`-intercepted keys. Test inside `:terminal`.

## Phase 5 — Navigation
- [ ] 23. Follow `[[link]]`/`#tag` under cursor (picker if the block has several).
- [ ] 24. Following a link to a nonexistent page creates it.
- [ ] 25. Back/forward history (e.g. `Ctrl-O`/`Ctrl-I`-style, if non-conflicting).
- [ ] 26. "Go to today's journal" key.
- [ ] 27. Jump from a backlink to its source block.

## Phase 6 — Persistence & external edits
- [ ] 28. Autosave on block commit / page switch / quit. Atomic write (temp file + rename).
- [ ] 29. Record mtime on load; pre-save mtime check → prompt overwrite / reload / cancel if changed on disk.
- [ ] 30. Poll open page's mtime every 1–2s; if changed and no unsaved edits, silent reload, restore cursor by block position.
- [ ] 31. Ignore `*.sync-conflict-*` and Syncthing temp files (`.syncthing.*.tmp`) when indexing.

## Phase 7 — MVP acceptance
- [ ] 32. Run the core loop by hand inside Vim `:terminal`: launch → journal → edit blocks (indent, multi-line, code, properties, TODO) → link → follow → backlinks → quit.
- [ ] 33. Open the files in a plain editor; confirm they're valid markdown.
- [ ] 34. Syncthing test: edit on a second device while the app is open → silent reload / prompt behaves.

## Explicitly post-MVP
Conflict merge, rename-with-reference-update, search/fuzzy finder, query blocks, block refs, graph view, git history.
