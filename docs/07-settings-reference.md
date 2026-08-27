# 7. Settings Reference

Every user-facing setting the addon defines or overrides, with its owner,
default, and consumer.

---

## 7.1 Scene properties

Registered in [`core/scene_state.py`](../roblox_tools/core/scene_state.py) onto
`bpy.types.Scene`, so they are **saved in the `.blend`** and travel with the
file. The rationale, from the module docstring: these describe *the thing being
built* — grid size, ground height, which pivot the handles hang off — not how
the user likes the tool to feel.

### Transform settings — shared by every tool

| Property | Type | Default | Values | Shown in | Read by |
| --- | --- | --- | --- | --- | --- |
| `rotools_orientation` | `Enum` | `'GLOBAL'` | `GLOBAL` (World), `LOCAL` | Every tool | `gizmo_common.orientation_frame` |
| `rotools_pivot_mode` | `Enum` | `'CENTER'` | `CENTER`, `ORIGIN`, `SWIVEL` | Every tool | `pivot.pivot_point` |
| `rotools_scale_pivot` | `Enum` | `'OPPOSITE_FACE'` | `OPPOSITE_FACE`, `CENTER` | Scale tool | `scale_gizmo.draw_prepare` |

`rotools_orientation` and `rotools_pivot_mode` are **deliberately scene-wide
rather than per-tool**, matching Roblox Studio's single Local-space toggle in
the Model tab. Scale and Rotate previously hardcoded `orient_type='LOCAL'`
while only Move had a control, so the Move tool's World setting was silently
contradicted the moment you switched tools.

- `Ctrl+L` (`rotools.toggle_orientation`) flips World ↔ Local from any tool.
- `Ctrl+Shift+L` (`rotools.cycle_pivot`) steps Center → Origin → Swivel,
  skipping Swivel when none is set.
- `rotools_scale_pivot` is greyed out in `SWIVEL` mode: a picked swivel
  outranks the opposite-face anchor.

See [12-swivel-and-pivot.md](12-swivel-and-pivot.md) for what each pivot mode
resolves to.

### Swivel settings

| Property | Type | Default | Shown in | Read by |
| --- | --- | --- | --- | --- |
| `rotools_swivel_element` | `Enum` | `'AUTO'` | Tool rows, in SWIVEL mode | `set_swivel` → `picking.pick_element` |
| `rotools_swivel_is_set` | `Bool` | `False` | (state) | `pivot.swivel_point`, `ui/overlay.py` |
| `rotools_swivel_point` | `Float[3]` (`XYZ`) | `(0,0,0)` | (state) | `pivot.swivel_point` |
| `rotools_swivel_normal` | `Float[3]` (`XYZ`) | `(0,0,1)` | (state) | `ui/overlay.py` |
| `rotools_swivel_kind` | `String` | `""` | Tool rows, as a label | display only |

`rotools_swivel_element` values are `AUTO`, `VERTEX`, `EDGE`, `FACE`.

### Transform-snap proxies

| Property | Type | Drives | Shown in |
| --- | --- | --- | --- |
| `rotools_snap_move` | `Bool` (`get`/`set`) | `use_snap` + `use_snap_translate` | Move tool |
| `rotools_snap_scale` | `Bool` (`get`/`set`) | `use_snap` + `use_snap_scale` | Scale tool |
| `rotools_snap_rotate` | `Bool` (`get`/`set`) | `use_snap` + `use_snap_rotate` | Rotate tool |

These have **no storage of their own** — they are computed views over Blender's
own tool settings. See §7.3.

### Dragger settings

| Property | Type | Default | Range | Shown in | Read by |
| --- | --- | --- | --- | --- | --- |
| `rotools_drag_grid_snap` | `Bool` | `True` | — | Select tool row 1 | `drag.py` → `resolve_snap(use_grid=)` |
| `rotools_drag_grid_size` | `Float` (`DISTANCE`) | `1.0` | `min=0.0`, `soft_max=16.0` | Select tool row 1 | `drag.py` → `resolve_snap(grid_size=)` |
| `rotools_drag_soft_snap` | `Bool` | `True` | — | Select tool row 2 | `drag.py` → `resolve_snap(use_soft=)` |
| `rotools_drag_surface_align` | `Bool` | `True` | — | Select tool row 2 | `drag.py:_orientation` |
| `rotools_drag_use_ground` | `Bool` | `True` | — | Select tool row 3 | `DragScene(use_ground=)` |
| `rotools_drag_ground_z` | `Float` (`DISTANCE`) | `0.0` | unbounded | Select tool row 3 | `DragScene(ground_z=)` |

Notes:

- **`rotools_drag_grid_size` is in Roblox studs**, and the addon treats
  1 stud = 1 Blender unit. Setting it to `0.0` disables grid snapping
  regardless of `rotools_drag_grid_snap`, because both `resolve_snap` and
  `drag.py` guard on `grid_size > 0.0`.
- **`rotools_drag_grid_snap` outranks `rotools_drag_soft_snap`.** When grid
  snap is on and the size is positive, the soft pass never runs. The Soft Snap
  toggle is greyed out while Grid is on to say so. See
  [05-snapping-engine.md](05-snapping-engine.md#54-snap-precedence--resolve_snap).
- `rotools_drag_surface_align` can be overridden per-drag by holding **Alt** —
  but pressing **T** re-imposes alignment, because tipping is a request to put
  a specific face against the surface.
- Both snap toggles can be inverted per-drag by holding **Shift**. Neither
  override is ever written back to these properties.
- `rotools_drag_ground_z` is unbounded in both directions — a negative ground
  is legal.

---

## 7.2 Addon preferences

Registered in [`core/preferences.py`](../roblox_tools/core/preferences.py) as
`RoToolsPreferences`. These are **per-user**, stored in Blender's preferences,
not in the `.blend`.

| Preference | Type | Default | Range | Read by |
| --- | --- | --- | --- | --- |
| `box_select_threshold` | `Int` (px) | `5` | `1`–`50` | `select.py` |
| `soft_snap_margin` | `Int` (px) | `12` | `1`–`100` | `drag.py`, `picking.py` |
| `swivel_marker_size` | `Int` (px) | `9` | `3`–`40` | `ui/overlay.py` |
| `use_tool_shortcuts` | `Bool` | `True` | — | `core/keymaps.py` |

The three pixel values are **screen-space**, not world distances.

- `box_select_threshold` — how far the mouse must travel from the press before
  a click becomes a drag. Compared squared against squared pixel delta, so no
  square root is taken.
- `soft_snap_margin` — how close the reference point must get to a vertex or
  edge midpoint before the dragger snaps onto it, and how close the cursor must
  be for the swivel picker's AUTO mode to prefer a vertex or edge over the
  face. **Converted through `pixels_to_world` at the point's depth every
  frame**, so the pull feels identical zoomed in and zoomed out. This is the
  project's hard rule: never hardcode a flat world-space margin.
- `use_tool_shortcuts` — gates all four global `Ctrl+1..4`
  bindings, which shadow Blender's own. Its `update` callback calls
  `keymaps.refresh()`, which re-applies the bindings **and** calls
  `wm.keyconfigs.update()`; see
  [03-tools-and-keymaps.md](03-tools-and-keymaps.md) for why that second call
  is required.

### `PACKAGE` and one accessor

```python
PACKAGE = __package__.rpartition(".")[0]     # -> roblox_tools

def get_pref(context, name):
    prefs = get_prefs(context)
    if prefs is None:
        return RoToolsPreferences.bl_rna.properties[name].default
    return getattr(prefs, name)
```

Two things this fixes. Readers used to repeat the declared default as a literal
fallback (`... if addon else 5`), which drifts the moment one of the two is
edited; `get_pref` falls back to the *declared* default instead. And the old
`__package__.split(".")[0]` returns `bl_ext` when the addon is installed as an
extension (`bl_ext.<repo>.roblox_tools.core`), finding no preferences at all —
`rpartition` is correct for both installation styles.

---

## 7.3 Blender settings the addon reads or writes

RoTools deliberately drives Blender's **native** snapping for the gizmo tools,
rather than inventing a parallel system, because the gizmos delegate to
`transform.*`.

| Blender property | Surfaced in | Written by RoTools? |
| --- | --- | --- |
| `tool_settings.use_snap` | All three transform tools, via the proxies | **Yes**, when a proxy is switched on |
| `tool_settings.use_snap_translate` | Move tool, via `rotools_snap_move` | **Yes** |
| `tool_settings.use_snap_scale` | Scale tool, via `rotools_snap_scale` | **Yes** |
| `tool_settings.use_snap_rotate` | Rotate tool, via `rotools_snap_rotate` | **Yes** |
| `tool_settings.snap_elements` | Move + Scale tool rows | No |
| `tool_settings.snap_angle_increment_3d` | Rotate tool row | **Yes — 15° on scenes still at Blender's default** |
| `space_data.overlay.grid_scale` | Move tool row, only when `'INCREMENT'` is an active snap element | No |
| `tool_settings.transform_pivot_point` | Not surfaced | No — **overridden** per-operator with `center_override` |

### Why the snapping needs a proxy

> **Verified in 5.2**: `use_snap` is the master ("Snap during transform").
> `use_snap_translate` / `use_snap_rotate` / `use_snap_scale` say which modes
> obey it, and **`use_snap_rotate` and `use_snap_scale` both default to
> `False`** while `use_snap_translate` defaults `True`.

Exposing either half alone produces a button that lies. The Rotate tool used to
expose only `use_snap_rotate` (does nothing while the master is off) and the
Scale tool only `use_snap` (leaves `use_snap_scale` off). The proxies read
`use_snap and <mode flag>` and, on write, set the mode flag plus the master
when enabling. Disabling leaves the master alone, so switching off Move snap
does not silently kill Rotate snap.

### The rotate increment

```python
BLENDER_DEFAULT_ANGLE_INCREMENT = radians(5)     # verified: 0.0872665
ROBLOX_ANGLE_INCREMENT = radians(15)

def _set_default_rotate_increment():
    for scene in bpy.data.scenes:
        ts = scene.tool_settings
        if abs(ts.snap_angle_increment_3d - BLENDER_DEFAULT_ANGLE_INCREMENT) < 1e-6:
            ts.snap_angle_increment_3d = ROBLOX_ANGLE_INCREMENT
```

Roblox Studio's own default. Deferred one tick because `bpy.data` is not
accessible during registration (restricted context), and the timer is
unregistered in `unregister()` if it has not fired.

The guard is the point: this used to overwrite every scene on **every addon
enable**, so a user who set their own increment lost it on the next Blender
start. Now only scenes still sitting on Blender's default are nudged — "set a
default", not "reassert a default forever". It is still not restored on
`unregister()`.

### `center_override`

Every gizmo forces its transform operator's centre to the pivot it draws at.
Without that, `transform.rotate` and `transform.resize` fall back to
`tool_settings.transform_pivot_point` — `MEDIAN_POINT` by default, `CURSOR` for
anyone who has used the pivot pie menu — and the handles and the transform
disagree. See [12-swivel-and-pivot.md](12-swivel-and-pivot.md#121-the-three-modes).

---

## 7.4 Constants that are not user-settable

| Constant | Value | Location | Meaning |
| --- | --- | --- | --- |
| `PIVOT_GRAB_PIXELS` | `12.0` | `operators/drag.py` | Click within this many px of the pivot to drag by the pivot instead of a bbox corner |
| `QUARTER_TURN` | `radians(90)` | `operators/drag.py` | One `R` spin step during a drag |
| `SNAP_PRIORITY` | `('VERTEX','EDGE','FACE')` | `core/snapping.py` | Soft-snap precedence, best to worst |
| `ELEMENT_PRIORITY` | `('VERTEX','EDGE','FACE')` | `core/picking.py` | Swivel AUTO precedence, best to worst |
| `ARROW_LENGTH` | `0.9` | `gizmos/move_gizmo.py` | Move arrow length |
| `HANDLE_GAP` | `0.12` | `gizmos/move_gizmo.py` | Gap between the bbox face and the arrow tail |
| `HANDLE_GAP` | `0.3` | `gizmos/scale_gizmo.py` | How far scale handles reach past the bbox face |
| `RADIUS_PADDING` | `1.15` | `gizmos/rotate_gizmo.py` | Rotate ring radius multiplier |
| `MIN_RADIUS` | `0.5` | `gizmos/rotate_gizmo.py` | Floor for the rotate ring radius |
| `AXIS_COLORS` | red/green/blue | `core/gizmo_common.py` | Per-axis handle colour |
| `HIGHLIGHT_COLOR` | `(1.0, 0.9, 0.2)` | `core/gizmo_common.py` | Amber hover colour — now shared, was duplicated in all three gizmo modules |
| `LINE_WIDTH` | `2.0` | `ui/overlay.py` | Swivel marker / preview line width |

---

## 7.5 Quick reference — where each control lives in the UI

```
Toolbar (Object Mode, 3D Viewport)
├── Roblox Select                    ← Ctrl+1
│   ├── [Grid ▣] [size]              rotools_drag_grid_snap / _grid_size
│   ├── [Soft Snap ▣]                rotools_drag_soft_snap  (greyed while Grid is on)
│   ├── [Align ▣]                    rotools_drag_surface_align
│   ├── [Ground ▣] [height]          rotools_drag_use_ground / _ground_z
│   └── (orientation/pivot block)
├── Roblox Move                      ← Ctrl+2
│   └── (orientation/pivot block)
│       [Snap ▣] [elements] [Increment]      rotools_snap_move
├── Roblox Scale                     ← Ctrl+3
│   └── (orientation/pivot block)
│       [Opposite Face | Center]     rotools_scale_pivot  (greyed in SWIVEL mode)
│       [Snap ▣] [elements]          rotools_snap_scale
└── Roblox Rotate                    ← Ctrl+4
    └── (orientation/pivot block)
        [Snap ▣] [Increment]         rotools_snap_rotate / snap_angle_increment_3d

orientation/pivot block, drawn by ui/tool_ui.py on every tool:
    [World | Local]                          rotools_orientation      (Ctrl+L)
    [Center ▾] [Set Swivel] [✕]              rotools_pivot_mode       (Ctrl+Shift+L, V)
    [Auto ▾] [Vertex]                        only in SWIVEL mode

Preferences ▸ Add-ons ▸ RoTools
├── Box Select Drag Threshold (px)   default 5,  range 1–50
├── Soft Snap Margin (px)            default 12, range 1–100
├── Swivel Marker Size (px)          default 9,  range 3–40
└── Tool Shortcuts ▣                 default on — Ctrl+1..4
```
