# RoTools — Project Rules

RoTools is a Blender addon (`roblox_tools/`) that recreates Roblox Studio's
Select/Move/Scale/Rotate tool behavior inside Blender. It uses Blender's
`bpy` operator/gizmo/tool API (bl_info, register/unregister pattern).

## NO GUESSING — hard rule

Never guess. This applies to:

- **Blender API behavior**: don't assume how an operator, gizmo, or property
  works. Look it up (bundled RST docs via the `blender` MCP server's
  `search_api_docs`/`get_python_api_docs`, or `search_manual_docs`) or read
  existing code in this repo that already does it.
- **Scene/object/data state**: don't assume names, transforms, modifiers, or
  hierarchy. Inspect the actual `.blend` state first (`get_objects_summary`,
  `get_object_detail_summary`, `get_blendfile_summary_*`, or read the file)
  before writing code that depends on it.
- **Existing code structure**: don't assume a function, class, or module
  exists or has a given signature. Read the file first (Grep/Read/Explore).
- **Root cause of bugs**: don't assume the cause. Reproduce or trace it
  before proposing a fix.

If the information needed isn't available and can't be looked up, stop and
ask the user rather than filling the gap with an assumption. State
uncertainty explicitly instead of presenting a guess as fact.

## Stay on task

- Do only what was asked. No speculative refactors, no unrelated cleanup,
  no new abstractions "while we're in there."
- If you notice an unrelated problem, mention it — don't fix it unless asked.
- Keep changes scoped to the module(s) relevant to the request
  (`core/`, `gizmos/`, `operators/`, `tools/`, `ui/`).
- Match the existing register/unregister + `MODULES` tuple pattern in
  [__init__.py](roblox_tools/__init__.py) when adding new modules — don't
  invent a different registration mechanism.
- Don't add error handling, validation, or fallbacks for cases that can't
  occur given Blender's API guarantees.

## Documentation as memory

Because this project has no git history to lean on, treat docs as the
project's persistent memory:

- Log notable decisions, gotchas, and in-progress work in
  [PROJECT_NOTES.md](PROJECT_NOTES.md) as you go (why something was built a
  particular way, known limitations, things tried and rejected).
- Keep this file (`CLAUDE.md`) updated if project-wide rules or the module
  layout change.
- When a module's purpose or public API changes meaningfully, update any
  docstring/comment at its top rather than leaving it stale.

## Layout

- `core/` — shared state, bounds/pivot math, preferences, gizmo helpers, plus
  two engines:
  - the dragger's: `snapping.py` (BVH cache, broad/narrow phase, snap
    priority) and `view_math.py` (screen↔world; every pixel-based threshold
    must go through `pixels_to_world`, never a flat world-space number)
  - the swivel picker's: `picking.py` (one vertex/edge/face off the polygon
    under the cursor — deliberately *not* the triangulated BVH, whose "edges"
    include triangulation diagonals the user cannot see)
- `gizmos/` — custom gizmo classes (move, scale, rotate). All three take their
  frame from `gizmo_common.orientation_frame` and their pivot from
  `pivot.pivot_point`, and must force that pivot onto the transform operator as
  `center_override` so what is drawn and what is transformed cannot diverge.
- `operators/` — bpy operators (select, drag, toggle orientation, set swivel)
- `tools/` — bpy ToolDef definitions binding operators+gizmos into toolbar tools
- `ui/` — the shared tool-settings rows (`tool_ui.py`) and the viewport overlay
  draw handler (`overlay.py`). There are no `bpy.types.Panel`s; all tool UI is
  each ToolDef's `draw_settings`.

Orientation (`rotools_orientation`) and pivot (`rotools_pivot_mode`) are
**scene-wide and shared by every tool**, matching Roblox Studio's single
Local-space toggle. Do not reintroduce per-tool copies.
