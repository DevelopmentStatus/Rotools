# 6. Gizmos

Three `GizmoGroup` subclasses, one per transform tool. All three follow the
same pattern: build handles once in `setup()`, reposition them every redraw in
`draw_prepare()`, and let a Blender `transform.*` operator do the actual work.

| Class | Module | Bound to | Handles | Target operator |
| --- | --- | --- | --- | --- |
| `ROTOOLS_GGT_move` | [move_gizmo.py](../roblox_tools/gizmos/move_gizmo.py) | `rotools.move_tool` | 6 face arrows + 1 centre ring | `transform.translate` |
| `ROTOOLS_GGT_scale` | [scale_gizmo.py](../roblox_tools/gizmos/scale_gizmo.py) | `rotools.scale_tool` | 6 box handles | `transform.resize` |
| `ROTOOLS_GGT_rotate` | [rotate_gizmo.py](../roblox_tools/gizmos/rotate_gizmo.py) | `rotools.rotate_tool` | 3 dial rings | `transform.rotate` |

---

## 6.1 Two rules all three obey

### The drawn frame and the operator's frame come from one call

```python
rotation_3x3, axis_rotations, orient_type = orientation_frame(context)
```

`gizmo_common.orientation_frame` returns **what is drawn** (`axis_rotations`,
and `rotation_3x3` for measuring bounds) together with **what the operator
constrains to** (`orient_type`). Setting one without the other draws handles
along one set of axes while transforming along another — which is exactly what
happened before: Scale and Rotate hardcoded `orient_type = 'LOCAL'` while only
Move had a control, so the Move tool's World setting was contradicted the
moment you switched tools.

World gives the identity frame and `'GLOBAL'`; Local gives the active object's
scale-stripped basis and `'LOCAL'`.

### The drawn pivot is forced onto the operator

```python
pivot = pivot_point(context, rotation_3x3)
...
op.center_override = pivot
```

Scale and Rotate both do this in **every** mode. Without it they fall back to
`tool_settings.transform_pivot_point` — `MEDIAN_POINT` by default, `CURSOR` for
anyone who has used the pivot pie menu — so the handles are drawn around one
point and the part transforms around another.

`transform.translate` has no `center_override` and needs none; a translation
has no pivot. The Move gizmo still positions its centre ring at `pivot_point`
so the active pivot is visible.

See [12-swivel-and-pivot.md](12-swivel-and-pivot.md) for the three pivot modes.

---

## 6.2 Shared setup

All three declare:

```python
bl_space_type  = 'VIEW_3D'
bl_region_type = 'WINDOW'
bl_options     = {'3D', 'SCALE'}
```

and gate on the same condition:

```python
@classmethod
def poll(cls, context):
    return context.mode == 'OBJECT' and context.selected_objects
```

**Verified** (`bpy.types.GizmoGroup.bl_options`):

| Flag | Meaning |
| --- | --- |
| `3D` | "Use in 3D viewport" |
| `SCALE` | "Scale to respect zoom (otherwise zoom independent display size)" |

`SCALE` is the load-bearing one. Without it a gizmo group draws at a constant
on-screen size regardless of camera distance. All three RoTools gizmos size
themselves from the selection's real bounds, so they must respect zoom or the
handles would detach from the geometry they annotate.

---

## 6.3 `core/gizmo_common.py`

### `AXIS_COLORS` and `HIGHLIGHT_COLOR`

```python
AXIS_COLORS = {'X': (0.9, 0.15, 0.2),      # red
               'Y': (0.35, 0.85, 0.15),    # green
               'Z': (0.15, 0.4, 0.95)}     # blue

HIGHLIGHT_COLOR = (1.0, 0.9, 0.2)          # amber
```

`HIGHLIGHT_COLOR` lives here now; the literal used to be repeated verbatim in
all three gizmo modules. `style_handle(gz, color)` applies the whole shared
look — colour, `alpha = 0.9`, the amber highlight at `alpha_highlight = 1.0`,
and `use_draw_modal = True` so a handle stays visible while its transform
operator runs.

### `AXIS_ROTATIONS` and `FLIP_ROTATION`

Blender's arrow, dial, and primitive gizmo primitives all point along their
**local +Z**. `AXIS_ROTATIONS` rotates that default direction onto each world
axis:

```python
{'X': Matrix.Rotation(radians(90),  4, 'Y'),
 'Y': Matrix.Rotation(radians(-90), 4, 'X'),
 'Z': Matrix.Identity(4)}
```

Checking the two non-trivial entries:

- **X:** rotating `(0,0,1)` about Y by +90° gives `(1,0,0)` = world +X ✓
- **Y:** rotating `(0,0,1)` about X by −90° gives `(0,1,0)` = world +Y ✓

`FLIP_ROTATION = Matrix.Rotation(radians(180), 4, 'X')` points a handle down the
negative side of its axis. Both the Move and Scale gizmos need it now that both
have six handles.

### `local_basis_matrix(active_object)`

```python
return active_object.matrix_world.to_3x3().normalized().to_4x4()
```

Strips the scale out of the active object's world matrix, leaving its
orientation basis.

> **Verified** in Blender 5.2.0 LTS: `Matrix.normalized()` returns a
> **column**-normalized matrix (for 4×4, the translation column is left
> untouched). It normalizes column lengths but does **not** orthogonalize — a
> shear matrix's normalized columns still had a dot product of 0.447. So for a
> sheared or skewed object the resulting "axes" are unit length but not
> mutually perpendicular, and the gizmo will draw a non-orthogonal frame. This
> is not handled; in practice Roblox-style part editing does not produce shear.

---

## 6.4 Move gizmo — `ROTOOLS_GGT_move`

**Six arrows, one on each bounding-box face**, plus one `GIZMO_GT_move_3d`
centre ring (`draw_style='RING_2D'`, `scale_basis = 0.16`, white at 60 % alpha).

This is the single most visible difference between the two tools. Blender's own
move gizmo draws three double-ended axes from a centre point; Roblox Studio
draws six arrows sitting on the part's faces, so you push the face you want to
move. Studio's version is what makes the tool read as "shove the part" rather
than "adjust a value".

```python
ARROW_LENGTH = 0.9
HANDLE_GAP   = 0.12        # gap between the bbox face and the arrow tail
HANDLES      = [(axis, sign) for axis in 'XYZ' for sign in (1, -1)]
```

Each arrow targets `transform.translate` with `release_confirm = True` and a
single-axis `constraint_axis`; both the `+X` and `−X` handles constrain to X,
and the operator's own modal follows the mouse along that axis either way. The
centre ring sets no constraint, so it is a free screen-space move.

### Handle placement

```python
mins, maxs = local_aabb(objects, rotation_3x3)
mid        = aabb_center(mins, maxs)
bounds     = {1: maxs, -1: mins}

scalars    = list(mid)
scalars[i] = bounds[sign][i] + sign * HANDLE_GAP
position   = point_from_local(rotation_3x3, *scalars)
```

**Verified in-viewport**: a 2 × 3.2 × 1.2 part produced exactly 7 gizmos at
±1.12 X, ±1.72 Y, ±0.72 Z — the bbox face centres plus `HANDLE_GAP` — with the
ring at the pivot.

Two fallbacks put every arrow at the pivot instead:

- **SWIVEL pivot mode** — the whole point of setting a swivel is to work from
  it, so the arrows radiate from the picked point.
- **A selection of nothing but Empties** — there is no box to sit on.

> **Observation:** `GIZMO_GT_arrow_3d` in `'NORMAL'` draw style renders three
> glyphs per handle — a stem, a box part-way along, and a cone at the tip — so
> six arrows are busier than Studio's six clean cones. Blender's own Move tool
> gizmo draws box handles too, so this is stock styling rather than something
> this addon introduced. `draw_style`'s full enum could not be read at runtime
> (`draw_style` is a dynamic property, absent from `gz.bl_rna.properties`), so
> alternatives were left unguessed. Recorded in
> [11-known-gaps.md](11-known-gaps.md).

---

## 6.5 Scale gizmo — `ROTOOLS_GGT_scale`

Six handles: `HANDLES = [(axis, sign) for axis in 'XYZ' for sign in (1, -1)]`.

### Why arrows, not cubes

```python
# GIZMO_GT_primitive_3d ('CUBE'/'PLANE') doesn't respect gz.color for its fill
# (renders bright white regardless) - arrow_3d does, so use a short stem that
# starts at the bounding-box face and ends HANDLE_GAP beyond it.
gz.draw_style = 'BOX'
gz.length     = HANDLE_GAP        # 0.3
```

A `GIZMO_GT_arrow_3d` in `'BOX'` draw style is a short stem with a box on the
end, and it *does* honour `gz.color`. This is a recorded workaround, not a
stylistic preference.

### Handles track the real bounding box

Each handle sits at the **centre of its bounding-box face**, in the current
orientation frame, and reaches `HANDLE_GAP` beyond it via the arrow's own
length. So the handles track the selection's real size instead of floating at a
fixed distance from a pivot.

`local_aabb` / `point_from_local` are a matched pair: the first projects world
points onto the frame's axes to get scalar bounds, the second reconstructs a
world point from those scalars. See
[08-module-reference.md](08-module-reference.md).

### The anchor, in three cases

```python
swivel = swivel_point(scene) if scene.rotools_pivot_mode == 'SWIVEL' else None
use_opposite_face = swivel is None and scene.rotools_scale_pivot == 'OPPOSITE_FACE'
center = pivot_point(context, rotation_3x3)
...
if use_opposite_face:
    anchor    = list(mid)
    anchor[i] = bounds[-sign][i]          # the face on the FAR side
    op.center_override = point_from_local(rotation_3x3, *anchor)
else:
    op.center_override = swivel if swivel is not None else center
```

| Case | Anchor | Result |
| --- | --- | --- |
| `OPPOSITE_FACE` (default) | The face opposite the handle | Dragging `+X` anchors the `−X` face, so the part grows in `+X` only — Roblox Studio's Scale behaviour |
| `CENTER` | The active pivot | Blender-style symmetric scaling |
| Pivot mode is `SWIVEL` | The picked point | A picked swivel outranks the scale anchor; it would be strange for it to steer Move and Rotate but not Scale |

**Verified** (`bpy.ops.transform.resize`): `center_override` is documented as
"Center Override, Force using this center value (**when set**)".

The old `CENTER` branch *unset* the property instead of assigning one, which
handed the pivot back to `tool_settings.transform_pivot_point`. It also wrapped
the unset in a `try/except Exception`:

> **Verified**: probing `OperatorProperties` directly, assigning
> `center_override` makes `is_property_set` true, `property_unset` clears it,
> and `property_unset` **does not raise**. The guard protected nothing. Both it
> and the call are gone, since the anchor is now always assigned.

---

## 6.6 Rotate gizmo — `ROTOOLS_GGT_rotate`

Three `GIZMO_GT_dial_3d` rings, one per axis, with `draw_options = {'CLIP'}` so
the far half of each ring is hidden behind the object. Each targets
`transform.rotate` with `orient_axis = axis`, `release_confirm = True`, plus the
shared `orient_type` and `center_override`.

### Radius

```python
mins, maxs  = local_aabb(objects, rotation_3x3)
half_extent = [(maxs[i] - mins[i]) / 2.0 for i in range(3)]
enclosing   = (hx**2 + hy**2 + hz**2) ** 0.5
center      = point_from_local(rotation_3x3, *aabb_center(mins, maxs))
reach       = enclosing + (pivot - center).length
return max(MIN_RADIUS, reach * RADIUS_PADDING)
```

The half-diagonal of the bounding box is the radius of the **sphere enclosing
that box**, so the rings wrap the object rather than sitting at an arbitrary
fixed world size. `RADIUS_PADDING = 1.15`, floored at `MIN_RADIUS = 0.5` so a
tiny or zero-size selection still gets grabbable rings.

The `(pivot - center).length` term is what makes the swivel usable: a swivel
picked on a face sits on the box surface, and a ring sized only to the box
centre would be drawn *inside* the part it rotates. Adding the pivot's distance
gives the sphere centred on the pivot that still encloses the box. When the
pivot **is** the box centre the term is zero, so this reduces exactly to the
previous behaviour.

This also closes an old mismatch: the rings used to be **positioned** from
object origins but **sized** from geometry bounds, so an object whose origin sat
outside its mesh got rings that did not enclose it. Both now come from
`pivot_point` / `local_aabb` in the same frame.

### Snap increment

The Rotate tool's settings row drives `rotools_snap_rotate` (which sets both
`use_snap` and `use_snap_rotate` — see
[07-settings-reference.md](07-settings-reference.md#73-blender-settings-the-addon-reads-or-writes))
and `tool_settings.snap_angle_increment_3d`.

**Verified**: `ToolSettings.snap_angle_increment_3d` is "Angle used for rotation
increments in 3D editors (in [0, 3.14159], **default 0.0872665**)" — Blender's
own default is 5°, and RoTools nudges it to Roblox's 15° on scenes still
sitting on that default.

---

## 6.7 What every gizmo measures

All three take their object list from `pivot.transform_objects(context)`:

```python
UNBOUNDED_TYPES = {'EMPTY'}

def transform_objects(context):
    return [obj for obj in context.selected_objects if obj.type not in UNBOUNDED_TYPES]
```

Shared with the dragger so the two cannot disagree about what "the selection"
means.

> **Verified** in Blender 5.2.0 LTS: an Empty's `bound_box` reads as eight zero
> vectors, so all eight of its transformed corners collapse onto its origin. A
> selected Empty used to drag the bounding-box centre toward itself and inflate
> the scale/rotate handle extents; the dragger already excluded Empties, the
> gizmos did not.
