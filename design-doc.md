# Terminal Outliner — Design Doc

## Summary
A Logseq-style block outliner, usable inside a Vim terminal buffer. Keyboard-driven TUI, daily-journal-centric, markdown files as source of truth.

## Stack
- **Language/UI**: Python + Textual
- **Environment**: runs inside Vim `:terminal` / nested terminal contexts. No tmux, no mouse support.
- **Keybinds**: explicitly designed to avoid conflicting with Vim's own bindings.

## Data Model
- **Source of truth**: `.md` files, one page = one file, flat directory (no folders).
- **Cache/index**: SQLite, fully rebuilt from files on every app startup (no incremental reconciliation in v1).
- **Block IDs**: ephemeral. Assigned as UUIDs at parse time, held only in memory/cache, never persisted into the markdown. Full reparse on every launch means no ID-drift concerns across restarts.
- **No transclusion.** Block refs (if implemented) are navigation-only (jump-to-block, backlinks) — not live-embedded content.
- **Linking**: `[[page links]]` and `#tags`, Logseq syntax. Renaming a page auto-updates all references to it. No graph view planned (if built later, must render inline in the TUI — not via external image viewer).

## Content Model
- Outliner blocks: indent/outdent, bullet-based, standard Logseq mechanics.
- Multi-line blocks supported (paragraphs, not just single lines).
- Code blocks with syntax highlighting.
- Block properties: `key:: value` syntax (Logseq-style). No compatibility guarantee with other markdown tools — considered out of scope.
- Task states: `TODO` / `DOING` / `DONE` (and similar Logseq/org-mode-style markers) — in scope for core loop.

## Journal
- Daily notes are the primary entry point of the app (Logseq-style). App should land on today's journal on launch.

## Sync
- **Transport**: Syncthing. Continuous, zero-friction background sync between devices. No git, no manual commit/push step in v1.
- **Conflict handling** (post-MVP): custom-built, not Syncthing's default. Watch for `*.sync-conflict-*` files; on detection, parse both versions, keep the local version as the base, and **append only the blocks from the conflict version whose text doesn't already appear in the page** (append, don't discard), then reparse and delete the conflict file. Naively concatenating both versions would duplicate every unchanged block. No block-ID reconciliation needed since IDs are ephemeral — block identity for dedup is exact text match. Consequence: a block edited on one device appears twice (old + new text) after merge; that's intentional — nothing is silently lost, user cleans up by hand.
- **External edits while app is open** (MVP): record the open page's mtime on load. Poll it every ~1–2s; if it changed and there are no unsaved edits, silently reload (restoring cursor by block position). Before every save, re-check mtime; if the file changed on disk, prompt overwrite / reload / cancel.
- **No version history** in v1 (git-based history is a possible future layer — see below).
- **Mobile**: no dedicated mobile app. Point any existing mobile markdown editor at the Syncthing-synced folder for offline editing. The app's merge logic absorbs whatever changes come back from those edits.

## Search & Query (deferred, not core)
- Full-text/fuzzy search: later.
- Logseq-style `{{query}}` blocks: nice-to-have, later.

## Core Loop (build this first)
1. Launch app → lands on today's journal.
2. Create/edit blocks: indent/outdent, multi-line, code blocks, `key:: value` properties, task states.
3. `[[Link]]` to a page; follow the link.
4. See backlinks on the linked page.
5. Quit — file on disk is valid, plain markdown.
6. Syncthing propagates it to other devices automatically.

Conflict-file merging (see Sync) is **not** part of the core loop / MVP.

## Deferred / Future Work
- **Graph view**: if built, must render inline in the TUI (e.g. via Mermaid + a terminal graphics protocol like Kitty/Sixel), not by shelling out to an external viewer.
- **Git-based history**: if added, run as a decoupled local layer (periodic commits on exit/idle) — not the sync transport, not the conflict-resolution mechanism. Git's line-level diff/move-detection could be used to approximate block history/lineage, but only as a forensic/debugging aid layered on top of ephemeral IDs — not a replacement for them.
- **Format compatibility** with generic markdown tools/parsers: explicitly out of scope.
- Full-text search, fuzzy finder, query blocks.

## Open Questions (not yet decided, non-blocking for core loop)
- Exact keybinding scheme (beyond "avoid Vim conflicts").
- Whether any block-ref/backlink navigation UI is built alongside `[[page links]]`, or links alone are sufficient for v1.
- Startup performance ceiling before "full reparse every launch" needs revisiting.
