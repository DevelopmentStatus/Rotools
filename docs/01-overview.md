# 1. Overview

## What RoTools is

RoTools is a Blender addon (`roblox_tools/`) that adds four toolbar tools to
the 3D Viewport. Move, Scale, and Rotate work in both Object Mode and Edit
Mesh (on vertex/edge/face selections); Select is Object Mode only:

| Toolbar tool | `bl_idname` | Gizmo | What it does |
| --- | --- | --- | --- |
| Roblox Select | `rotools.select_tool` | *(none)* | Click-select, and free-drag parts across surfaces |
| Roblox Move | `rotools.move_tool` | `ROTOOLS_GGT_move` | Three axis arrows + a centre ring |
| Roblox Scale | `rotools.scale_tool` | `ROTOOLS_GGT_scale` | Six box handles on the bounding box faces |
| Roblox Rotate | `rotools.rotate_tool` | `ROTOOLS_GGT_rotate` | Three dial rings sized to the selection |

The addon does **not** replace Blender's own tools; it registers alongside
them, inserted after `builtin.select_box` in the toolbar
(`roblox_tools/tools/select_tool.py:61`).

## The design premise

Roblox Studio's manipulation model differs from Blender's in four ways that
this addon deliberately reproduces:

1. **The Select tool is the dragger.** In Studio there is no separate "move by
   dragging the body" tool — dragging a part with Select picks it up and slides
   it over other surfaces; dragging empty space rubber-band selects. RoTools
   wires both into one operator, `rotools.select`, gated by an `allow_drag`
   property. See [04-dragger.md](04-dragger.md).
2. **Parts rest on surfaces.** A dragged part's bounding box lands *flush* on
   whatever is under the cursor — no penetration, no floating gap — and (by
   default) tips over to lie against a wall it is dragged onto.
3. **Scaling grows from the opposite face.** Studio's Scale handles anchor the
   far side of the part, so dragging the +X handle extends the part in +X
   rather than growing symmetrically about the centre. RoTools reproduces this
   with `transform.resize`'s `center_override`.
4. **Round-number placement is the default.** Studio ships with a 1-stud move
   increment and a 15° rotate increment enabled. RoTools defaults to grid snap
   on at 1.0 unit, and sets `snap_angle_increment_3d` to 15°.

## Roblox ↔ Blender concept mapping

| Roblox Studio | RoTools equivalent | Implementation |
| --- | --- | --- |
| Select tool (doubles as dragger) | `rotools.select_tool` | `rotools.select` with `allow_drag=True` → `rotools.drag` |
| Move tool handles | `ROTOOLS_GGT_move` arrows | `GIZMO_GT_arrow_3d` → `transform.translate` |
| Scale tool handles | `ROTOOLS_GGT_scale` boxes | `GIZMO_GT_arrow_3d` (BOX style) → `transform.resize` |
| Rotate tool rings | `ROTOOLS_GGT_rotate` dials | `GIZMO_GT_dial_3d` → `transform.rotate` |
| 1 stud | 1 Blender unit | `rotools_drag_grid_size` default `1.0` |
| Move increment (studs) | `rotools_drag_grid_size` | `core/scene_state.py:165` |
| Rotate increment (15°) | `snap_angle_increment_3d` | `core/scene_state.py:55` (`ROBLOX_ANGLE_INCREMENT`) |
| Baseplate | Synthetic infinite ground plane | `core/snapping.py:170` |
| Surface alignment on drop | `rotools_drag_surface_align` | `operators/drag.py:211` |
| World / Local space toggle (Ctrl+L, any tool) | `rotools_orientation` | `operators/toggle_orientation.py` |
| Pivot from a picked vertex / edge / face | `rotools_pivot_mode = 'SWIVEL'` | `operators/set_swivel.py`, `core/picking.py` |
| Ctrl+1/2/3/4 tool shortcuts | Same bindings | `core/keymaps.py:17-20` |
| Ctrl+D duplicate | `rotools.duplicate` | `operators/duplicate.py` |
| `CanCollide` | `Collidable` custom Boolean property | `core/snapping.py:DragScene.candidates` |

## Feature matrix

| Capability | State | Notes |
| --- | --- | --- |
| Click / Shift-add / Ctrl-toggle select | ✅ | Delegates to `view3d.select` |
| Drag-from-empty-space box select | ✅ | Delegates to `view3d.select_box`, mode chosen from modifiers |
| Free-drag a part across surfaces | ✅ | Tiers 0–2 of the priorities plan |
| Flush resting placement | ✅ | See the derivation in [04-dragger.md](04-dragger.md) |
| Surface-align (tip onto walls) | ✅ | Alt overrides per-drag |
| Synthetic ground plane | ✅ | Analytic, infinite, Z-up |
| Vertex / edge / face soft snap | ✅ | Only when grid snap is off — see precedence in [05](05-snapping-engine.md) |
| Grid snap | ✅ | Hard snap outranks soft snap |
| Shift = invert snapping, Alt = keep orientation | ✅ | Per-frame override, never written to scene state |
| Status-bar key hints + live snap readout | ✅ | `workspace.status_text_set` with a callable |
| Move / Scale / Rotate gizmos | ✅ | Delegate to Blender's `transform.*` operators |
| Global / Local orientation, shared across every tool | ✅ | Ctrl+L, `rotools_orientation` |
| Center / Origin / Swivel pivot, shared across every tool | ✅ | Ctrl+Shift+L, `rotools_pivot_mode` |
| Opposite-face vs Centre scale pivot | ✅ | `rotools_scale_pivot` |
| Ctrl+D drag-stamp duplication | ✅ | `operators/duplicate.py` |
| Move / Scale / Rotate in Edit Mesh (vertex/edge/face selections) | ✅ | Gizmo-only — `rotools.select`'s body-click drag stays Object Mode |
| Per-object "collidable" filtering | ✅ | `Collidable` custom property on an object, read by `DragScene.candidates` |
| `ui/` package | ✅ | `ui/tool_ui.py` (shared tool-settings rows) + `ui/overlay.py` (viewport draw handler) — no `bpy.types.Panel`, by design |

## Compatibility

| | |
| --- | --- |
| `bl_info["blender"]` (declared minimum) | `(4, 0, 0)` |
| Verified against | Blender **5.2.0 LTS**, Python 3.13 |
| Addon version | `(0, 3, 0)` |
| Context mode | Object Mode (all four tools) + Edit Mesh (Move, Scale, Rotate — two `WorkSpaceTool` classes per tool, one per mode, sharing one `bl_idname`) |
| Space | `VIEW_3D` |

The declared 4.0 minimum has **not** been tested; every runtime confirmation in
these docs was made on 5.2.0 LTS. See [11-known-gaps.md](11-known-gaps.md).

## Scale of the codebase

30 Python files (5 empty `__init__.py`), ~3,000 lines total. The largest
modules are the ones carrying the novel behaviour:

```
operators/drag.py       412   free-drag operator (placement + modal loop)
core/scene_state.py     252   scene-level properties
core/snapping.py        240   collision + snap engine
ui/overlay.py           195   viewport draw handler (swivel marker + HUD text)
core/bounds.py          164   AABB math shared by gizmos and the dragger
operators/set_swivel.py 162   picked-element pivot operator
gizmos/rotate_gizmo.py  145   dial rings, per-ring radius
gizmos/move_gizmo.py    140   axis arrows + centre ring
gizmos/scale_gizmo.py   128   opposite-face scale handles
core/picking.py         123   vertex/edge/face picker under the cursor
core/pivot.py           111   shared Center/Origin/Swivel resolution
operators/select.py     111   click / box-select / drag routing
core/preferences.py     103   addon preferences
operators/duplicate.py   89   Ctrl+D drag-stamp duplication
core/view_math.py        51   screen ↔ world conversion
```
