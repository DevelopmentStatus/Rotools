# 3. Tools and Keymaps

## The four `WorkSpaceTool` definitions

All four share `bl_space_type = 'VIEW_3D'` and `bl_context_mode = 'OBJECT'`,
so they appear in the 3D Viewport toolbar in Object Mode only.

| | Select | Move | Scale | Rotate |
| --- | --- | --- | --- | --- |
| `bl_idname` | `rotools.select_tool` | `rotools.move_tool` | `rotools.scale_tool` | `rotools.rotate_tool` |
| `bl_label` | Roblox Select | Roblox Move | Roblox Scale | Roblox Rotate |
| `bl_icon` | `ops.generic.select` | `ops.transform.translate` | `ops.transform.resize` | `ops.transform.rotate` |
| `bl_widget` | `None` | `ROTOOLS_GGT_move` | `ROTOOLS_GGT_scale` | `ROTOOLS_GGT_rotate` |
| LMB binds | `rotools.select` **with `allow_drag=True`** | `rotools.select` | `rotools.select` | `rotools.select` |
| Extra binds | `Ctrl+L`, `Ctrl+Shift+L`, `V` | same | same | same |
| Registered after | `builtin.select_box` | `rotools.select_tool` | `rotools.move_tool` | `rotools.scale_tool` |

All four now carry the same three extra bindings:

| Binding | Operator | Effect |
| --- | --- | --- |
| `Ctrl+L` | `rotools.toggle_orientation` | Flip World ↔ Local (Roblox Studio's own Ctrl+L) |
| `Ctrl+Shift+L` | `rotools.cycle_pivot` | Step Center → Origin → Swivel, skipping Swivel when none is set |
| `V` | `rotools.set_swivel` | Pick the swivel pivot — see [12-swivel-and-pivot.md](12-swivel-and-pivot.md) |

These live in each tool's own `bl_keymap`, so they only apply while that tool
is active — unlike `core/keymaps.py`'s global `Object Mode` bindings. **Verified**
that plain `V` is unbound in both `Object Mode` and `3D View` (only `Ctrl+V` is
taken, by `view3d.pastebuffer`).

Only Select passes `separator=True, group=True` to `register_tool`
([select_tool.py:49](../roblox_tools/tools/select_tool.py)), which puts a
divider before the RoTools block and starts a nested tool group.

### `allow_drag` is the only difference in the LMB binding

All four tools bind the *same* operator on LMB press. Select passes
`allow_drag=True`; the other three pass `None` (operator defaults, so
`allow_drag=False`). The reason is stated at
[select.py:13-16](../roblox_tools/operators/select.py): Move / Scale / Rotate
need plain click-select, and a body drag there would fight their gizmos.

The property is passed through `bl_keymap`'s third element:

```python
bl_keymap = (
    (
        "rotools.select",
        {"type": 'LEFTMOUSE', "value": 'PRESS'},
        {"properties": [("allow_drag", True)]},
    ),
)
```

**The `properties` value must be a list of tuples, not a dict.** Blender's own
`bl_keymap_utils/io.py:_init_properties_from_data` asserts this; a dict fails
silently, leaving `allow_drag` at its default and quietly disabling the
dragger. Recorded in `PROJECT_NOTES.md`.

## Tool settings rows (`draw_settings`)

Each tool draws its own settings into the topbar. There are no
`bpy.types.Panel`s; this is the entire UI surface of the addon. The rows the
tools share live in [ui/tool_ui.py](../roblox_tools/ui/tool_ui.py) —
`draw_orientation_row` and `draw_snap_row` — because per-tool copies are how
they drifted apart in the first place.

Every tool draws the orientation/pivot block:

```
[ World | Local ]                   rotools_orientation (expand=True)
[ Center ▾ ][ Set Swivel ][ ✕ ]     rotools_pivot_mode + the swivel operators
[ Auto ▾ ][ Vertex ]                only in SWIVEL mode: element + what is set
```

### Roblox Select — [select_tool.py:28](../roblox_tools/tools/select_tool.py)

Three rows, all bound to Scene properties, all feeding the dragger:

```
[ Grid ▣ ][ 1.0 m        ]      rotools_drag_grid_snap / _grid_size
[ Soft Snap ▣ ][ Align ▣ ]      rotools_drag_soft_snap / _surface_align
[ Ground ▣ ][ 0.0 m       ]     rotools_drag_use_ground / _ground_z
```

The size and height fields are placed in a `sub` row whose `.active` tracks its
toggle, so they grey out when their feature is off.

### Roblox Move — [move_tool.py](../roblox_tools/tools/move_tool.py)

```
(orientation/pivot block)
[ Snap ▣ ][ elements ][ Increment ]     rotools_snap_move
```

### Roblox Scale — [scale_tool.py](../roblox_tools/tools/scale_tool.py)

```
(orientation/pivot block)
[ Opposite Face | Center ]              rotools_scale_pivot, greyed in SWIVEL mode
[ Snap ▣ ][ elements ]                  rotools_snap_scale
```

### Roblox Rotate — [rotate_tool.py](../roblox_tools/tools/rotate_tool.py)

```
(orientation/pivot block)
[ Snap ▣ ][ Increment ]                 rotools_snap_rotate
                                        tool_settings.snap_angle_increment_3d
```

### The `rotools_snap_*` proxies

These rows drive **Blender's own** transform snapping, because the gizmos
delegate to `transform.translate` / `resize` / `rotate`. Blender splits that in
two, and exposing either half alone does not work:

> **Verified in 5.2**: `use_snap` is the master ("Snap during transform").
> `use_snap_translate` / `use_snap_rotate` / `use_snap_scale` say which modes
> obey it — and **`use_snap_rotate` and `use_snap_scale` both default to
> `False`** while `use_snap_translate` defaults `True`.

So the Rotate tool's old row, which exposed only `use_snap_rotate`, toggled a
flag that did nothing while the master was off; the Scale tool's, which exposed
only `use_snap`, left `use_snap_scale` off. Either way the button lied.

`rotools_snap_move` / `_scale` / `_rotate`
([core/scene_state.py](../roblox_tools/core/scene_state.py)) are `get`/`set`
proxies with no storage of their own. They read `use_snap and <mode flag>` — so
they are true only when the transform will really snap — and on write set the
mode flag, plus the master when enabling. Disabling deliberately leaves the
master alone, so turning off Move snap does not silently kill Rotate snap.

## Global keyboard shortcuts

[`core/keymaps.py`](../roblox_tools/core/keymaps.py) registers four items into
the **`Object Mode`** keymap (`space_type='EMPTY'`) on the *addon* keyconfig,
each invoking `rotools.switch_tool` with a `tool_id`:

| Shortcut | Tool | Rationale |
| --- | --- | --- |
| `Ctrl+1` | Select | Roblox Studio's own exact shortcuts |
| `Ctrl+2` | Move | " |
| `Ctrl+3` | Scale | " |
| `Ctrl+4` | Rotate | " |

`rotools.switch_tool` is a one-line wrapper around `wm.tool_set_by_id`
([switch_tool.py:12](../roblox_tools/operators/switch_tool.py)). It exists
because keymap items pass properties to *one* operator, and binding
`wm.tool_set_by_id` directly would work but would not carry the addon's own
`UNDO` option or give the bindings a single identifiable idname to unregister.

`unregister()` removes exactly the items it added, tracked in the
module-level `addon_keymaps` list.

## Shortcut conflicts with Blender's defaults

**Verified** by enumerating the resolved *user* keyconfig in a live Blender
5.2.0 LTS session with the addon enabled. These bindings are not additive —
they shadow existing behaviour:

| Key | RoTools binds (keymap) | Blender default (keymap) | Effect |
| --- | --- | --- | --- |
| `Ctrl+1` … `Ctrl+4` | `rotools.switch_tool` (**Object Mode**) | `object.subdivision_set` (**Object Mode**) | **Direct shadow**, same keymap, RoTools ordered first. Subdivision-level shortcuts are unavailable while the addon is enabled. |

Because the addon only binds into the **Object Mode** keymap, Edit Mode's `R`,
`E`, `S` and friends are untouched.

**Mitigation:** the whole set is behind the **Tool Shortcuts** addon
preference (`use_tool_shortcuts`, default on). Turning it off unregisters all
four items immediately and gives `Ctrl+1..4` back.

> The `bpy.context.window_manager.keyconfigs.update()` inside
> `keymaps.refresh()` is what makes "immediately" true. **Verified**: removing
> the items from the *addon* keyconfig took it from 8 → 0 while the resolved
> *user* keyconfig still listed all 8, because it is a cached merge — so `R`
> stayed shadowed. With `update()`, the user count drops to 0 at once and
> returns to 8 when the preference goes back on.

## Modifier semantics, by context

| Modifier | During click-select | During box-select | During a drag |
| --- | --- | --- | --- |
| *(none)* | Replace selection (`deselect_all=True`) | `mode='SET'` | Snap per the scene toggles |
| `Shift` | Extend (`extend=True`) | `mode='ADD'` | **Invert** every snap toggle for as long as held |
| `Ctrl` | Toggle (`toggle=True`) | `mode='SUB'` | `Ctrl+D` stamps a copy; plain Ctrl unbound |
| `Shift+Ctrl` | Toggle path (`extend` and `toggle` both set) | `mode='AND'` | Shift behaviour applies |
| `Alt` | — | — | Keep the original orientation (skip surface align) |

Plain Ctrl is still unbound during a drag — there is no verified Roblox
meaning for a Ctrl-drag to copy — but `Ctrl+D` now stamps, and two unmodified
keys were added:

| Key | During a drag |
| --- | --- |
| `R` | Spin the selection 90° about the drop surface's normal (world +Z when free-dragging) |
| `T` | Tip it onto the next of its six faces |
| `Ctrl+D` | Stamp a copy at the current position and keep dragging the original |

See [04-dragger.md](04-dragger.md).
