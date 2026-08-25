# 12. Pivot Modes and the Swivel

Added 2026-08-25. All three transform gizmos hang off one shared pivot, and one
of the three modes is a point you pick off a piece of geometry.

---

## 12.1 The three modes

`scene.rotools_pivot_mode`, declared in
[core/scene_state.py](../roblox_tools/core/scene_state.py), resolved by
[core/pivot.py](../roblox_tools/core/pivot.py):

| Mode | Pivot | Why it exists |
| --- | --- | --- |
| `CENTER` *(default)* | Centre of the selection's bounding box, measured in the current orientation frame | A Roblox part's `CFrame` **is** its centre, so this is the Studio-matching mode |
| `ORIGIN` | Median of the selected objects' world origins | Blender's own habit; an origin that was deliberately placed is a reasonable thing to pivot on |
| `SWIVEL` | A vertex / edge midpoint / face centre picked with `rotools.set_swivel` | The one this page is about |

Verified the first two actually differ: a 4-unit cube at the origin plus a
1-unit cube at X=10 gives `ORIGIN` = **5.0** and `CENTER` = **4.25** (the box
spans −2 … 10.5).

`SWIVEL` with nothing picked yet falls through to `CENTER` rather than dropping
the handles at the world origin, and the tool settings row says so in as many
words instead of leaving the user to wonder why nothing moved.

### `center_override` is not optional

Every gizmo pushes the resolved pivot onto its transform operator:

```python
op.center_override = pivot
```

Without it, `transform.rotate` and `transform.resize` fall back to
`tool_settings.transform_pivot_point` — `MEDIAN_POINT` by default, `CURSOR` for
anyone who has used the pivot pie menu. The rings would be drawn around one
point and the part would spin around another. `transform.translate` has no
`center_override` and needs none: a translation does not have a pivot.

> **Verified**: `transform.rotate` *does* expose `center_override`, documented
> as "Force using this center value (when set)". `transform.translate` does
> not.

---

## 12.2 Setting a swivel

`rotools.set_swivel` ([operators/set_swivel.py](../roblox_tools/operators/set_swivel.py))
is modal, bound to plain **V** in each RoTools tool's own `bl_keymap`.

| Key | Effect |
| --- | --- |
| Move mouse | Live-preview the element under the cursor |
| `LMB` | Commit, and switch `rotools_pivot_mode` to `SWIVEL` |
| `Esc` / `RMB` | Cancel |
| `Tab` | Cycle Auto → Vertex → Edge → Face |
| `A` / `V` / `E` / `F` | Jump straight to Auto / Vertex / Edge / Face |

It is modal rather than a one-shot click so the element can be seen before it is
taken. Committing switches the pivot mode because setting a swivel and then not
using it is never what was meant; `rotools.clear_swivel` puts it back to
`CENTER`.

> **Why plain `V` is safe.** Verified against the resolved user keyconfig: `V`
> alone is unbound in both `Object Mode` and `3D View` (only `Ctrl+V` is taken,
> by `view3d.pastebuffer`). And a ToolDef `bl_keymap` only applies while that
> tool is active, unlike `core/keymaps.py`'s global `Object Mode` bindings.

---

## 12.3 `core/picking.py` — why not the BVH

The dragger already has a nearest-vertex/edge/face engine in
[core/snapping.py](../roblox_tools/core/snapping.py). The picker does **not**
use it, on purpose.

`snapping.py` builds `BVHTree.FromPolygons(..., all_triangles=True)`. Its
"edges" are therefore triangle edges, which include **triangulation diagonals
that do not exist in the mesh the user is looking at**. Snapping an edge the
user deliberately clicked onto an invisible diagonal is indefensible.

So `pick_element` takes the face index from `scene.ray_cast` and reads that
polygon straight off the evaluated mesh: an n-gon's four real edges are the four
candidates, and its centre is the real face centre.

> **Verified, and load-bearing**: `scene.ray_cast` returns the **original**
> object, but its `location` / `normal` / `index` belong to the **evaluated**
> object's mesh. A subdivided cube raycast down its Z axis reported `index 20`
> of the evaluated mesh's 24 polygons, and that polygon's corners contained the
> reported hit point. The lookup must go through `evaluated_get(depsgraph)`;
> indexing `obj.data` would read a completely different mesh.

Normals are transformed by the **inverse transpose** of the object matrix, not
the matrix. Roblox-style building scales axes freely and the plain matrix would
skew the normal.

### AUTO ordering

`ELEMENT_PRIORITY = ('VERTEX', 'EDGE', 'FACE')`, matching the dragger's own snap
priority. Vertex wins if it is within the `soft_snap_margin` pixel radius of the
cursor, then edge on the same test, then face unconditionally — so AUTO
gracefully degrades to the face out in the middle of one.

Verified on a default cube:

| Cursor over | AUTO returns |
| --- | --- |
| Near a top corner | `VERTEX (1, 1, 1)` |
| Near a top edge midpoint | `EDGE (0, 1, 1)` |
| Middle of the top face | `FACE (0, 0, 1)` |
| Empty space | `None` |

Note the cursor must be **on** a face: aimed at the exact projected silhouette
corner the ray grazes past the mesh and misses, which is inherent to a
raycast-based picker.

---

## 12.4 The overlay

[ui/overlay.py](../roblox_tools/ui/overlay.py) is one `POST_VIEW` draw handler
on `SpaceView3D`. It draws the swivel marker (a screen-constant axis cross plus
a dot) whenever the pivot mode is `SWIVEL` and a point is set, and the live pick
preview — including the edge or face loop under the cursor — while
`rotools.set_swivel` runs.

It bails out unless one of the four RoTools tools is active, so it does not
litter Blender's own tools.

Two decisions worth keeping:

- **Depth test off**, like the 3D cursor. A pivot you cannot see because it is
  inside the part is worse than one that floats over it.
- **Cross arms sized through `pixels_to_world`**, per this project's rule that a
  pixel threshold never becomes a flat world-space number.

> Builtin shader uniforms, from the 5.2 API reference rather than memory:
> `POLYLINE_UNIFORM_COLOR` takes `vec2 viewportSize`, `float lineWidth`,
> `vec4 color`; `POINT_UNIFORM_COLOR` takes `vec4 color`, `float size`. Both
> take a `vec3 pos` attribute.

---

## 12.5 Orientation on top

`scene.rotools_orientation` (World / Local) applies to all three pivot modes
identically — the swivel is a **pivot point**, not an orientation.

This was checked rather than assumed. `transform.*`'s `orient_type` enum in 5.2
is `GLOBAL / LOCAL / NORMAL / GIMBAL / VIEW / CURSOR / PARENT` — there is **no
`CUSTOM` member**, so aligning the axes to a picked face's normal would have
needed the `orient_matrix` / `orient_matrix_type` pair. None of that is
necessary for "swivel from a set vert/edge/face".

`gizmo_common.orientation_frame(context)` returns the drawn frame *and* the
operator's `orient_type` in one call, specifically so the two cannot drift
apart. See [06-gizmos.md](06-gizmos.md).
