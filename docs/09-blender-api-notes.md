# 9. Blender API Notes

`CLAUDE.md` forbids guessing about Blender API behaviour. This file records the
API facts RoTools depends on, each with the source that established it, so a
future change can check an assumption instead of re-deriving it.

**Environment for every runtime probe below:** Blender **5.2.0 LTS**, Python
3.13, RoTools enabled from the repository path.

Legend:

- 📗 **Docs** — quoted from Blender's bundled Python API reference.
- 🔬 **Probe** — established by running code in a live Blender session.
- 📝 **Source** — established by reading Blender's own Python modules.

---

## 9.1 Geometry and math

### 📗 `BVHTree.FromPolygons(vertices, polygons, *, all_triangles=False, epsilon=0.0)`

> "BVH tree constructed from geometry passed in as arguments. […]
> `all_triangles`: Use when all polygons are triangles for more efficient
> conversion."

Used by `_build_tree`, which calls `mesh.calc_loop_triangles()` first so the
precondition holds.

### 📗 `BVHTree.find_nearest(origin, distance=…)` and `.ray_cast(origin, direction, distance=…)`

> "Returns a tuple: (position, normal, index, distance). Values will all be
> `None` if no hit is found."

`index` is the polygon index, which indexes the same `tris` list the tree was
built from — this is what makes the coarse → fine handoff in
`nearest_features` work without a second query.

`ray_cast`'s `direction` is documented as "normalized internally", but
`DragScene.ray_cast` still requires a normalized direction from the caller so
that the BVH's reported `distance` is comparable to the analytic ground
plane's. `mouse_ray` guarantees it.

### 📗 `Scene.ray_cast(depsgraph, origin, direction, *, distance=…)`

> "Cast a ray onto evaluated geometry in world-space"
> Returns `(result, location, normal, index, object, matrix)`.

Used for the two grab-time raycasts. **It has no way to exclude objects**,
which is the entire reason `DragScene` exists — see
[05-snapping-engine.md](05-snapping-engine.md#51-why-not-sceneray_cast).

### 📗 `Vector.rotation_difference(other)`

> "Returns a quaternion representing the rotational difference between this
> vector and another." 2D vectors raise `AttributeError`.

This is the surface-align rotation: `rest_axes[tip_index].rotation_difference(up)`.

### 🔬 `Matrix.normalized()` is column normalization, and does not orthogonalize

📗 The docstring reads: *"Return a column normalized matrix (3x3 and 4x4 only).
… for 4x4 matrices, the 4th column (translation) is left untouched."*

🔬 Confirmed at runtime, and confirmed that it does **not** orthogonalize:

| Input | Column lengths before | Column lengths after |
| --- | --- | --- |
| `Rotation(0.7,'Z') @ Diagonal(2,3,4)` | `2, 3, 4` | `1, 1, 1` |

For a shear matrix `[[1, 0.5, 0], [0, 1, 0], [0, 0, 1]]`, after
`.normalized()` the dot product of columns 0 and 1 was **0.447**, not 0.

**Consequence for RoTools:** `local_basis_matrix` produces unit-length axes but
not necessarily perpendicular ones for a sheared object. Not handled — see
[11-known-gaps.md](11-known-gaps.md).

### 🔬 `Object.bound_box` already reflects modifier-evaluated bounds

📗 The docs say only: *"Object's bounding box in object-space coordinates, all
values are -1.0 when not available."*

That leaves open whether it tracks modifier output, which matters because the
dragger's **broad phase** reads `obj.bound_box` while its **narrow phase**
builds a BVH from the *evaluated* mesh. If they disagreed, the broad phase
could reject an object the BVH would have hit.

🔬 Probed with a 1×1 plane carrying a 4-unit Solidify modifier, linked into the
active scene so the real depsgraph evaluated it:

| Measurement | Z range |
| --- | --- |
| `obj.bound_box` (original object) | −2 … 2 |
| `obj.evaluated_get(depsgraph).bound_box` | −2 … 2 |
| Evaluated mesh vertex Z range | −2 … 2 |

**They agree.** The broad phase and narrow phase are consistent; this is *not*
a source of missed collisions. (An earlier reading of the code suggested it
might be — the probe disproved it.)

### 🔬 An `EMPTY`'s `bound_box` reads as eight zero vectors

🔬 In Blender 5.2.0 LTS, a newly created `bpy.data.objects.new(name, None)`
reported `bound_box` as eight `(0, 0, 0)` triples — **not** the `-1.0` the docs
mention for the "not available" case.

**Consequence:** all eight transformed corners collapse onto the Empty's
origin, so a selected Empty contributes exactly its origin to any `local_aabb`.
`operators/drag.py` filters `type != 'EMPTY'` out of the dragged set; the
gizmos do not filter. See [06-gizmos.md](06-gizmos.md#66-the-pivot-and-a-caveat).

---

## 9.2 Operators

### 📗 `Operator.bl_options` flags used

From `operator_type_flag_items`:

| Flag | Documented meaning |
| --- | --- |
| `REGISTER` | "Display in the info window and support the redo toolbar panel." |
| `UNDO` | "Push an undo event when the operator returns `FINISHED` (needed for operator redo, mandatory if the operator modifies Blender data)." |
| `GRAB_CURSOR` | "Use so the operator grabs the mouse focus, enables wrapping when continuous grab is enabled." |
| `BLOCKING` | "Block anything else from using the cursor." |

`rotools.drag` uses all four; `rotools.select`, `rotools.switch_tool`, and
`rotools.toggle_orientation` use `{'UNDO'}` only.

### 📗 `transform.resize`'s `center_override`

> "Center Override, Force using this center value (**when set**)"

The "when set" is the operative phrase: it forces the pivot while set, and
reverts to the normal transform pivot once unset. That is why the scale
gizmo's `CENTER` mode calls `property_unset("center_override")` rather than
assigning a neutral value.

### 🔬 `event.shift` is still `True` on the shift-release event

Recorded in `PROJECT_NOTES.md` from in-session testing: on the `LEFT_SHIFT`
event whose `value` is `'RELEASE'`, `event.shift` still reads `True`.

**Consequence:** during a modifier key's own event, `event.value` is the
authority. `drag.py:_modifiers` exists solely for this, and `_apply` must never
read `event.shift` directly.

---

## 9.3 Tools, gizmos, and keymaps

### 📗 `bpy.utils.register_tool(tool_cls, *, after=None, separator=False, group=False)`

> `after`: "Optional identifiers this tool will be added after."
> `separator`: "When true, add a separator before this tool."
> `group`: "When true, add a new nested group of tools."

The four tools chain via `after={previous_idname}`, which is why their
registration order in `MODULES` is load-bearing.

### 📗 `GizmoGroup.bl_options`

> `3D` — "Use in 3D viewport."
> `SCALE` — "Scale to respect zoom (otherwise zoom independent display size)."

`SCALE` is required for all three RoTools gizmos because they size themselves
from real selection bounds.

### 📗 `WorkSpace.status_text_set(text)`

> "Set the status text or None to clear. When text is a function, this will be
> called with the (header, context) arguments."

Passing a **callable** is what makes the `EVENT_*` / `MOUSE_*` icons possible;
a plain string gets no icons. The callable receives a real `self.layout`.

Both `status_text_set(None)` and `area.header_text_set(None)` must be called on
`FINISHED` **and** `CANCELLED`, or the hints persist after the drag ends.

### 📝 `bl_keymap` properties must be a list of tuples

Blender's own `bl_keymap_utils/io.py:_init_properties_from_data` **asserts**
that the `"properties"` value is a list of tuples. A dict fails silently —
`allow_drag` stays at its default and the dragger is quietly disabled.

```python
{"properties": [("allow_drag", True)]}    # correct
{"properties": {"allow_drag": True}}      # silently does nothing
```

### 📗 `ToolSettings.snap_angle_increment_3d`

> "Angle used for rotation increments in 3D editors (in [0, 3.14159],
> **default 0.0872665**)"

Blender's default is 5°; RoTools overrides it to 15° (Roblox Studio's default)
at registration.

---

## 9.4 Registration-time constraints

### `bpy.data` is unavailable during `register()`

Blender's restricted context during addon registration means
`scene_state.register()` cannot iterate `bpy.data.scenes` inline. It defers via
`bpy.app.timers.register(_set_default_rotate_increment, first_interval=0)` —
one tick later the context is unrestricted.

The callback returns `None`, so it is a one-shot and never reschedules.

### 🔬 Keymap conflict resolution

🔬 Enumerated from the live `wm.keyconfigs` in a session with the addon
enabled. In the **resolved user keyconfig**, RoTools' `Object Mode` items are
ordered *ahead of* Blender's defaults in the same keymap:

| Key | RoTools item (keymap) | Blender default (keymap) |
| --- | --- | --- |
| `R` | `rotools.switch_tool` (Object Mode) | `transform.rotate` (Object Mode) |
| `Ctrl+1..4` | `rotools.switch_tool` (Object Mode) | `object.subdivision_set` (Object Mode) |
| `Q` | `rotools.switch_tool` (Object Mode) | `wm.call_menu` (Window) |
| `W` | `rotools.switch_tool` (Object Mode) | `wm.tool_set_by_id` (3D View) |
| `E` | `rotools.switch_tool` (Object Mode) | *(none in Object Mode)* |

The first two are same-keymap shadows, so those defaults are genuinely
unreachable while the addon is enabled. Full discussion:
[03-tools-and-keymaps.md](03-tools-and-keymaps.md#shortcut-conflicts-with-blenders-defaults).

---

## 9.5 Things deliberately *not* asserted

Kept here so nobody mistakes an unknown for a verified fact:

- **Blender 4.0 compatibility.** `bl_info` declares `(4, 0, 0)` as the minimum,
  but every check in this document was made on 5.2.0 LTS. The 4.0 claim is
  untested.
- **Whether `property_unset` can raise** in the scale gizmo's `CENTER` branch.
  The `try/except Exception` there guards a case that has not been shown to
  occur.
- **Handler-ordering rules between different keymaps** (`Object Mode` vs
  `3D View` vs `Window`) for the `Q` and `W` bindings. The keymaps each binding
  lives in were enumerated; the resolution rule between *different* keymaps was
  not independently confirmed.
- **`obj.name` uniqueness across linked libraries.** `DragScene` keys its
  caches by `obj.name`. Whether two library-linked objects can present the same
  `name` through `context.view_layer.objects` was not tested.
