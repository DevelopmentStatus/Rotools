# 8. Module Reference

Per-module public symbols. Line numbers are against the current working tree.

---

## `roblox_tools/__init__.py`

| Symbol | Kind | Notes |
| --- | --- | --- |
| `bl_info` | `dict` | name, author `RoTools`, version `(0,1,0)`, blender `(4,0,0)`, category `3D View` |
| `MODULES` | `tuple` | 16 modules in registration order — see [02-architecture.md](02-architecture.md#registration-lifecycle) |
| `register()` | function | Forward walk over `MODULES` |
| `unregister()` | function | Reverse walk over `MODULES` |

---

## `core/bounds.py`

AABB math shared by the gizmos (rotated frames) and the dragger (world frame).

| Symbol | Signature | Returns |
| --- | --- | --- |
| `AXIS_INDEX` | `{'X': 0, 'Y': 1, 'Z': 2}` | — |
| `axis_vectors` | `(rotation_3x3)` | The three columns as world-space unit axes |
| `local_aabb` | `(objects, rotation_3x3)` | `(mins, maxs)` — 3-tuples of **scalar projections** onto the frame's axes, not points |
| `point_from_local` | `(rotation_3x3, sx, sy, sz)` | World point reconstructed from those scalars |
| `world_aabb` | `(objects)` | `(Vector min, Vector max)` — `local_aabb` in the identity frame |
| `aabb_corners` | `(mins, maxs)` | The 8 corners, as `Vector`s |
| `aabb_overlap` | `(min_a, max_a, min_b, max_b)` | `bool` — broad-phase reject |
| `ray_hits_aabb` | `(origin, direction, mins, maxs)` | `bool` — slab test |

`local_aabb` and `point_from_local` are a **matched pair**: the first projects
world points onto a frame's axes to get scalar bounds; the second turns those
scalars back into a world point. The scale gizmo uses both to place handles on
bounding-box faces in the active object's rotated frame.

`ray_hits_aabb` handles the axis-parallel case explicitly (`abs(d) < 1e-9`:
the ray either starts inside the slab or misses) and rejects hits entirely
behind the origin (`t_far < 0.0`).

---

## `core/gizmo_common.py`

| Symbol | Kind | Notes |
| --- | --- | --- |
| `AXIS_COLORS` | `dict` | X red, Y green, Z blue |
| `AXIS_ROTATIONS` | `dict` | 4×4 rotations taking local +Z onto each world axis |
| `local_basis_matrix` | `(active_object) → Matrix` | `matrix_world.to_3x3().normalized().to_4x4()` |

See [06-gizmos.md](06-gizmos.md#62-coregizmo_commonpy--the-shared-basis) for the
`normalized()` caveat.

---

## `core/keymaps.py`

| Symbol | Kind | Notes |
| --- | --- | --- |
| `BINDINGS` | `tuple` | 4 `(key, ctrl, tool_id)` triples: Ctrl+1..4 |
| `addon_keymaps` | `list` | Module-level `(km, kmi)` registry for clean teardown |
| `register()` / `unregister()` | functions | Adds/removes items in the `Object Mode` keymap (`space_type='EMPTY'`) on the addon keyconfig |

`register()` returns early if `wm.keyconfigs.addon is None` (background mode).

---

## `core/pivot.py`

| Symbol | Signature | Returns |
| --- | --- | --- |
| `get_selection_pivot` | `(context)` | Median of `matrix_world.translation` over `context.selected_objects`, or `None` if nothing is selected |

**Median of object origins**, not of geometry. Used by the move gizmo, the
rotate gizmo, and the dragger's pivot-grab test.

---

## `core/preferences.py`

| Symbol | Kind | Notes |
| --- | --- | --- |
| `RoToolsPreferences` | `AddonPreferences` | `bl_idname = "roblox_tools"` |
| `.box_select_threshold` | `IntProperty` | default `5`, `1`–`50` |
| `.soft_snap_margin` | `IntProperty` | default `12`, `1`–`100` |
| `.draw(context)` | method | Two `layout.prop` rows |

---

## `core/scene_state.py`

| Symbol | Kind | Notes |
| --- | --- | --- |
| `ORIENTATION_ITEMS` | `tuple` | `GLOBAL` / `LOCAL` enum items |
| `SCALE_PIVOT_ITEMS` | `tuple` | `OPPOSITE_FACE` / `CENTER` enum items |
| `register()` | function | Adds 8 `bpy.types.Scene` properties, then defers the rotate-increment default |
| `_set_default_rotate_increment()` | function | Timer callback; sets `snap_angle_increment_3d = radians(15)` on every scene |
| `unregister()` | function | `del`s all 8 properties |

Full property table: [07-settings-reference.md](07-settings-reference.md).

---

## `core/snapping.py`

The collision + snapping engine. No `bpy.ops` dependency.

| Symbol | Kind | Notes |
| --- | --- | --- |
| `GROUND` | `str` sentinel | `'GROUND'` — used as `SurfaceHit.obj` for the synthetic plane |
| `SNAP_PRIORITY` | `tuple` | `('VERTEX', 'EDGE', 'FACE')`, best to worst |
| `SurfaceHit` | class (`__slots__`) | `.point`, `.normal`, `.obj`, `.distance` |
| `SnapResult` | class (`__slots__`) | `.kind` (`'VERTEX'`/`'EDGE'`/`'FACE'`/`'GRID'`/`None`), `.point` |
| `_build_tree(obj, depsgraph)` | function | `(BVHTree, verts, tris)` in **world space**, or `None` |
| `snap_to_grid(point, size)` | function | Round every axis to the nearest multiple |
| `_keep_closest(found, kind, point, distance)` | function | Keeps the nearest candidate per kind; stores `point.copy()` |
| `DragScene` | class | See below |
| `resolve_snap(...)` | function | See below |

### `DragScene`

```python
DragScene(context, dragged, use_ground=True, ground_z=0.0)
```

| Member | Kind | Notes |
| --- | --- | --- |
| `.depsgraph` | attr | From `context.evaluated_depsgraph_get()` |
| `.candidates` | attr | Visible `MESH` objects in the view layer, minus `dragged` |
| `.aabb(obj)` | method | Cached world AABB — broad phase only ever needs this |
| `.tree(obj)` | method | Cached `(BVHTree, verts, tris)`, built on first use; `None` if unusable |
| `.ray_cast(origin, direction)` | method | Nearest `SurfaceHit`, or `None`. `direction` **must be normalized** |
| `._ground_ray(origin, direction)` | method | Analytic infinite Z-up plane intersection |
| `.nearest_features(point, radius)` | method | `{kind: (world point, distance)}` for whichever of VERTEX/EDGE/FACE were found within `radius` |

Caches are keyed by `obj.name` and live exactly as long as the `DragScene` —
i.e. one drag.

### `resolve_snap`

```python
resolve_snap(drag_scene, reference, radius, grid_size, use_soft, use_grid) -> SnapResult
```

Hard grid snap wins outright when enabled; otherwise the soft pass runs in
`SNAP_PRIORITY` order; otherwise the reference is returned untouched. Full
decision table and the reasoning behind the precedence:
[05-snapping-engine.md](05-snapping-engine.md#54-snap-precedence--resolve_snap).

---

## `core/view_math.py`

Every pixel-based threshold in the addon goes through this module.

| Symbol | Signature | Wraps / derives |
| --- | --- | --- |
| `mouse_ray` | `(region, rv3d, coord) → (origin, direction)` | `region_2d_to_origin_3d` + `region_2d_to_vector_3d`; direction is normalized |
| `view_plane_point` | `(region, rv3d, coord, depth_point) → Vector` | `region_2d_to_location_3d` |
| `point_to_region` | `(region, rv3d, point) → Vector2 \| None` | `location_3d_to_region_2d`; `None` if behind the view |
| `pixels_to_world` | `(region, rv3d, point, pixels) → float` | Derived from `rv3d.window_matrix[1][1]` — see [05](05-snapping-engine.md#the-pixels_to_world-derivation) |

---

## `operators/select.py` — `rotools.select`

| | |
| --- | --- |
| `bl_idname` | `rotools.select` |
| `bl_label` | Roblox Select |
| `bl_options` | `{'UNDO'}` |
| `allow_drag` | `BoolProperty(default=False, options={'HIDDEN'})` |

| Method | Notes |
| --- | --- |
| `invoke` | Records start px, `shift`, `ctrl`; reads `box_select_threshold`; raycasts **only if `allow_drag`**; installs a modal handler |
| `_object_under_mouse(context)` | `scene.ray_cast` at the press position → the hit object or `None` |
| `_start_drag(context)` | Selects the grabbed object if it wasn't (Shift keeps the rest), sets it active, invokes `rotools.drag` |
| `modal` | Threshold → drag or box-select; release without drag → `view3d.select`; RMB/ESC → `CANCELLED` |

Box-select mode mapping: `Shift+Ctrl → 'AND'`, `Shift → 'ADD'`,
`Ctrl → 'SUB'`, neither → `'SET'`.

---

## `operators/drag.py` — `rotools.drag`

| | |
| --- | --- |
| `bl_idname` | `rotools.drag` |
| `bl_label` | Roblox Drag |
| `bl_options` | `{'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}` |
| `start_x`, `start_y` | `IntProperty(options={'HIDDEN'})` — the **press** position |
| `PIVOT_GRAB_PIXELS` | `12.0` |

| Method | Notes |
| --- | --- |
| `_signed_axes(matrix)` | *(module function)* All six signed local axes in world space, most-upward first. Index 0 is the resting axis; `T` steps through the rest |
| `_drag_roots(objects)` | *(module function)* `objects` minus any with a selected ancestor — writing a child's `matrix_world` and then its parent's applies the drag twice |
| `poll` | Object mode + non-empty selection |
| `invoke` | Builds all the cached grab state; three `CANCELLED` exits |
| `_pick_reference(...)` | Pivot if the click was within 12 px of it, else the nearest AABB corner |
| `_modifiers(event)` | `(shift, alt)`, correct on the modifier key's own event |
| `_apply(context, event)` | The per-frame placement pipeline |
| `_restore()` | Writes `start_matrices` back |
| `_status_draw / _status_set / _status_clear` | Status bar with `EVENT_*` icons |
| `_header_update(context)` | `Drag \| Snap: <kind>` live readout |
| `modal` | See the contract table in [04-dragger.md](04-dragger.md#45-the-modal-contract) |

Instance state created in `invoke`: `objects`, `grab_point`, `start_matrices`,
`rest_axes`, `movers`, `tip_index`, `spin_steps`, `stamps`,
`corner_offsets`, `reference_offset`, `drag_scene`,
`margin_pixels`, and `snap_kind` (set by `_apply`).

Full walkthrough: [04-dragger.md](04-dragger.md).

---

## `operators/toggle_orientation.py` — `rotools.toggle_orientation` + `rotools.cycle_pivot`

Flips `scene.rotools_orientation` between `GLOBAL` and `LOCAL` and reports
the new value. `bl_options = {'UNDO'}`. Bound to `Ctrl+L` in the Move tool's
`bl_keymap`.

---

## `operators/switch_tool.py` — `rotools.switch_tool`

| | |
| --- | --- |
| `tool_id` | `StringProperty` |
| `execute` | `bpy.ops.wm.tool_set_by_id(name=self.tool_id)` |

A one-line wrapper so the four keymap items have a single addon-owned idname
to bind and unregister.

---

## `tools/*.py` — the four `WorkSpaceTool`s

All share `bl_space_type = 'VIEW_3D'`, `bl_context_mode = 'OBJECT'`, and a
`draw_settings(context, layout, tool)` classmethod. Per-tool idnames, widgets,
keymaps, and settings rows: [03-tools-and-keymaps.md](03-tools-and-keymaps.md).

Registration uses `bpy.utils.register_tool(cls, after={...})` to fix toolbar
order; only Select passes `separator=True, group=True`.

**Verified** signature:
`register_tool(tool_cls, *, after=None, separator=False, group=False)`.

---

## `gizmos/*.py` — the three `GizmoGroup`s

| Class | `bl_idname` | Handles | Target operator |
| --- | --- | --- | --- |
| `ROTOOLS_GGT_move` | `ROTOOLS_GGT_move` | 3 × `GIZMO_GT_arrow_3d` + 1 × `GIZMO_GT_move_3d` | `transform.translate` |
| `ROTOOLS_GGT_scale` | `ROTOOLS_GGT_scale` | 6 × `GIZMO_GT_arrow_3d` (`BOX`) | `transform.resize` |
| `ROTOOLS_GGT_rotate` | `ROTOOLS_GGT_rotate` | 3 × `GIZMO_GT_dial_3d` | `transform.rotate` |

All three use `bl_options = {'3D', 'SCALE'}` and the same `poll`. Details:
[06-gizmos.md](06-gizmos.md).
