# RoTools Documentation

Reference documentation for **RoTools**, a Blender addon that recreates Roblox
Studio's Select / Move / Scale / Rotate tool behaviour inside Blender's
`bpy` operator / gizmo / tool API.

This folder documents the addon **as it exists in `roblox_tools/`**. It is
descriptive, not aspirational: where a feature is unbuilt or a file is stale,
that is recorded in [11-known-gaps.md](11-known-gaps.md) rather than papered over.

---

## Where to start

| If you want to… | Read |
| --- | --- |
| Understand what the addon does and why | [01-overview.md](01-overview.md) |
| Learn how the pieces fit together | [02-architecture.md](02-architecture.md) |
| Know what each toolbar tool binds | [03-tools-and-keymaps.md](03-tools-and-keymaps.md) |
| Understand the free-drag placement math | [04-dragger.md](04-dragger.md) |
| Understand collision + snap resolution | [05-snapping-engine.md](05-snapping-engine.md) |
| Understand the transform gizmos | [06-gizmos.md](06-gizmos.md) |
| Look up a setting's default or owner | [07-settings-reference.md](07-settings-reference.md) |
| Look up a function signature | [08-module-reference.md](08-module-reference.md) |
| Check a Blender API assumption | [09-blender-api-notes.md](09-blender-api-notes.md) |
| Install, reload, or package the addon | [10-development.md](10-development.md) |
| See what's broken, stale, or unfinished | [11-known-gaps.md](11-known-gaps.md) |
| Understand pivot modes and the swivel | [12-swivel-and-pivot.md](12-swivel-and-pivot.md) |

---

## Contents

1. **[Overview](01-overview.md)** — purpose, the Roblox ↔ Blender concept
   mapping, feature matrix, compatibility.
2. **[Architecture](02-architecture.md)** — module graph, registration
   lifecycle, state ownership, end-to-end event flow.
3. **[Tools and keymaps](03-tools-and-keymaps.md)** — the four `WorkSpaceTool`
   definitions, their keymaps and settings rows, plus the global shortcuts and
   the Blender defaults they shadow.
4. **[The dragger](04-dragger.md)** — `rotools.drag` in depth: handoff,
   grab state, the flush-placement derivation, modifier keys, modal contract.
5. **[Snapping engine](05-snapping-engine.md)** — `DragScene`, the
   broad → narrow → fine pipeline, the analytic ground plane, `resolve_snap`
   precedence, and pixel→world conversion.
6. **[Gizmos](06-gizmos.md)** — the three `GizmoGroup`s, the shared frame,
   why the drawn pivot is forced onto the operator, Roblox's six-arrow move
   handles, opposite-face scaling, and bounds-driven ring radius.
7. **[Settings reference](07-settings-reference.md)** — every scene property
   and addon preference: type, default, range, UI location, reader.
8. **[Module reference](08-module-reference.md)** — per-module public symbols
   and signatures.
9. **[Blender API notes](09-blender-api-notes.md)** — the specific API
   behaviours this addon depends on, each with its source or the probe that
   confirmed it.
10. **[Development](10-development.md)** — install, the reload order that
    avoids orphaning modules, recovery from a stuck tool registration,
    packaging.
11. **[Known gaps](11-known-gaps.md)** — stale artifacts, doc drift,
    unimplemented tiers, and behavioural sharp edges. §11.6 lists what has been
    closed, so it is not mistaken for a live backlog.
12. **[Pivot modes and the swivel](12-swivel-and-pivot.md)** — the three shared
    pivots, `rotools.set_swivel`, why the picker does not use the dragger's
    BVH, and the viewport overlay.

---

## Conventions used in these docs

- **Verified** marks a statement confirmed against Blender's bundled API
  reference or by running code in a live Blender 5.2.0 LTS session with the
  addon enabled. [09-blender-api-notes.md](09-blender-api-notes.md) records
  each one.
- **Observation** marks something read directly off the source that has *not*
  been exercised at runtime.
- Code references are given as `path:line` against the repository root.
- "Stud" means a Roblox stud, which this addon treats as exactly 1 Blender
  unit (see `rotools_drag_grid_size`).

## Relationship to the other project docs

- [`../CLAUDE.md`](../CLAUDE.md) — working rules for the repo (no-guessing
  rule, scope discipline, registration pattern). Normative for contributors.
- [`../PROJECT_NOTES.md`](../PROJECT_NOTES.md) — the running decision log.
  Newest first. This folder is the *structured* view; `PROJECT_NOTES.md`
  remains the chronological one, and is where new decisions get appended.
