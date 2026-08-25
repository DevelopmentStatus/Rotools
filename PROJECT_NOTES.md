# PROJECT_NOTES

Running log of decisions, gotchas, and in-progress work for RoTools. Newest
entries at the top. This is the project's persistent memory since there is
no git history to consult.

## 2026-08-25 — Rotate ring sizing and the half-drawn rings

**The rings were sized by the bounding *sphere*, and that is the wrong solid.**
`_radius` returned one number for all three rings: the half-diagonal of the
selection's AABB, `hypot(hx, hy, hz)`. That radius is dominated by the box's
*longest* axis, so a ring spanning only the two short ones came out far bigger
than the cross-section it wraps. On the 3.83x2x2 test cube the shared radius was
2.737 while the X ring (the YZ plane, a 2x2 square) only needed 1.626 — a 1.7x
overshoot, and the reason the rings ran off screen.

Replaced with a per-ring radius (`_radii`, keyed by axis). A ring turning about
axis `a` sweeps the selection around the line through the pivot along `a`, so
its radius is the farthest any of the part's corners sits **from that line** —
the perpendicular distance, which on an orthonormal frame is just the two
in-plane components:

    r = max over corners of hypot((c - pivot).u, (c - pivot).v)

with u, v the ring plane's two axes (`PLANE_AXES = {'X': (1, 2), 'Y': (2, 0),
'Z': (0, 1)}`). Padding aside this is the tightest circle that clears the part,
and it fixes the old pivot handling for free: the old code added the *full 3D*
`|pivot - centre|` to a 3D radius, a bound rather than a distance, so a swivel
offset purely along X inflated the X ring too even though the swivel sits dead
centre in that ring's own plane.

**The corners must be the part's own, never an AABB's — this is the whole
point.** First attempt measured the corners of the axis-aligned box fitted
around the selection. An AABB *swells as its contents turn*, so the ring grew
while you dragged it. Measured on the test slab, sweeping world Y and reading
the Y ring:

    rotation about Y   0deg    15     30     45     60     90
    from AABB corners  2.361  2.867  3.187  3.296  3.187  2.361   <- swells 40%
    from real corners  2.361  2.361  2.361  2.361  2.361  2.361   <- spread 0

Hence `bounds.world_corners(objects)`: the oriented corners, `bound_box` carried
through `matrix_world`. `local_aabb` now walks the same generator.

**Why this is the right invariant.** A rotation about `a` preserves every
point's distance from `a` — so the ring being dragged cannot change size during
its own drag, exactly, not approximately. Rings for the *other* two axes do
resize as the part turns, and that is correct: the part genuinely reaches
further from those lines.

**Verified.** 12 combinations (WORLD/LOCAL x CENTER/ORIGIN x XYZ), each stepped
through a full 360deg turn about the ring's own axis, driven the way the gizmo
drives it (`Translation(pivot) @ Rotation(t, axis) @ Translation(-pivot)`, i.e.
`center_override` + `orient_axis`). Worst spread over a full turn **6.4e-7**,
worst disagreement with a brute-force `(c - pivot).cross(axis).length` walk
**4.5e-7**. Both are float32 noise out of `obj.bound_box`.

> Careful when testing this: stepping one component of `rotation_euler` is
> **not** a rotation about that world axis unless the other two are zero (XYZ
> order means `R = Rz @ Ry @ Rx`). Doing it that way showed a bogus 0.08 spread
> on the X ring. Compose the rotation about the pivot explicitly instead.

**Only half of each ring was drawn — that was `draw_options = {'CLIP'}`.** The
dial gizmo's CLIP option cuts the circle at the view plane through its centre,
leaving just the camera-facing half. Blender's own rotate gizmo wants that;
Roblox's rings are whole circles, and the clipped half gives nothing to grab on
the far side. Now set to `set()` explicitly rather than left off, so nobody has
to know what the type's default is. Confirmed by screenshot after reload: three
complete circles.

> Sizing and clipping are independent — worth separating if this comes up
> again. Big rings ran off the *edges* of the region; CLIP punched the gap out
> of the *middle* of each ring, well inside the viewport.

**Not verified by screenshot the second time round.** The invariance fix was
confirmed numerically only — `get_screenshot_of_*` returned an all-black frame
for the whole Blender window, which is what a minimised/occluded window grabs.
The CLIP fix above *was* confirmed visually, before that happened.

**Still a flat world-space number: `MIN_RADIUS = 0.5`.** It is a floor on the
world radius, so a small part viewed from far away still gets a small on-screen
ring. A screen-space floor via `view_math.pixels_to_world` would be the honest
fix; not done, because nobody has asked and `draw_prepare` would need the region
and rv3d threaded in. Flagging it here rather than fixing it silently.

## 2026-08-25 — Tool pass: shared pivot/orientation, swivel, dragger QoL

A comparison pass over all four tools against Roblox Studio, plus the swivel
pivot. Everything below was verified in the live Blender 5.2.0 LTS, **loading
the repo from `sys.path` rather than the installed copy** — see the very last
section, this turned out to matter a lot.

### Bugs found and fixed

**The dragger double-transformed parented selections.** Setting `matrix_world`
on a child and then on its parent applies the drag twice. Measured: a child 2
units from its parent, both offset by +10 on X, landed at **X = 22** instead of
12 when the child was written first; parent-first gave the correct 12. And
`context.selected_objects` gives no ordering guarantee, so this was a coin
flip. `drag.py:_drag_roots` now writes only objects with no selected ancestor —
children ride along with their parents, which is also what Blender's own
transform does.

**Rotate and Scale rotated/scaled around a different point than they drew.**
Neither gizmo set `center_override`, so `transform.rotate` and (in CENTER mode)
`transform.resize` fell back to `tool_settings.transform_pivot_point`. That
defaults to MEDIAN_POINT, and is CURSOR for anyone who has used the pivot pie
menu — so the rings were drawn around the selection and the part span around
the 3D cursor. Both gizmos now force `center_override` to the same pivot they
draw at, in **every** mode. Verified `transform.rotate` does have
`center_override` (it is not documented alongside `resize`'s, but it is there).

**Rotate snapping never engaged, and neither did Scale's.** Blender splits
transform snapping into a master `use_snap` plus per-mode affect flags
`use_snap_translate` / `use_snap_rotate` / `use_snap_scale`. Verified in 5.2:
**`use_snap_rotate` and `use_snap_scale` both default to `False`** while
`use_snap_translate` defaults `True`. The Rotate tool's settings row exposed
only `use_snap_rotate`, which does nothing while the master is off; the Scale
tool exposed only the master, leaving `use_snap_scale` off. Either way the
button lied. Fixed with three `rotools_snap_*` proxy properties
(`core/scene_state.py`) that read true only when the transform will really
snap, and on write set the mode flag plus — when enabling — the master.
Disabling deliberately does *not* clear the master, so turning off Move snap
does not silently kill Rotate snap.

**`property_unset("center_override")` was guarded against nothing.** Probed it
directly on `OperatorProperties`: assigning sets `is_property_set` true,
`property_unset` clears it and does not raise. The `try/except Exception` in
`scale_gizmo.py` is gone — and so is the call, since the anchor is now always
forced.

**`__package__.split(".")[0]` is wrong for extensions.** Three call sites used
it to find the addon preferences. As a legacy addon `__package__` is
`roblox_tools.core`, so it worked; as an extension it is
`bl_ext.<repo>.roblox_tools.core` and `split(".")[0]` returns `bl_ext`, finding
nothing. Now one `PACKAGE = __package__.rpartition(".")[0]` in
`core/preferences.py`, correct for both.

**An unselectable object under the press ate the click.** `scene.ray_cast`
ignores `hide_select`, so pressing on one deselected everything and then handed
the dragger an object it refuses. `select.py` now treats an unselectable hit as
a miss, and also falls back to box-select when `rotools.drag` returns
CANCELLED, so a refused drag is never a dead click.

### Roblox parity

**Move now draws six arrows on the bounding-box faces**, not three on a central
tripod. This is the most visible difference between the two tools: Studio has
you push the face you want to move. The centre ring stays for free movement and
is where the pivot is shown. Verified in-viewport — 7 gizmos at exactly the
bbox face centres plus `HANDLE_GAP`, e.g. a 2 x 3.2 x 1.2 part gave handles at
±1.12 X, ±1.72 Y, ±0.72 Z.

**Orientation is now scene-wide, not per-tool.** Studio has one Local-space
toggle in the Model tab that every transform tool obeys. Scale and Rotate used
to hardcode `orient_type='LOCAL'` while only Move had a control, so the Move
tool's World setting was quietly contradicted the moment you switched tools.
`rotools_move_orientation` became `rotools_orientation`, Ctrl+L works from
every tool, and `gizmo_common.orientation_frame` returns the drawn frame and
the operator's `orient_type` **together** so they cannot drift apart again.

**Pivot became a first-class shared setting** — `CENTER` (bounding-box centre,
the Roblox default, since a part's CFrame *is* its centre), `ORIGIN` (median of
object origins, the old behaviour), `SWIVEL`. This also closes the "rotate
gizmo is centred on origins but sized from bounds" mismatch, since both now
come from the same place. Verified the modes actually differ: two cubes, a
4-unit at the origin and a 1-unit at X=10, gave origin-median **5.0** and
bbox-centre **4.25**.

**The 15° rotate increment is a default again, not an assertion.** It used to
be written to every scene on every addon enable, so a user who set their own
increment lost it on the next Blender start. Now only scenes still sitting on
Blender's own default (0.0872665 rad = 5°) get nudged. The deferred timer is
also unregistered on `unregister()`.

**The Q/W/E/R and Ctrl+1..4 shortcuts are opt-out** via a new
`use_tool_shortcuts` preference, because they shadow `transform.rotate` on R
and `object.subdivision_set` on Ctrl+1..4 in the same keymap.

> The `keyconfigs.update()` call in `keymaps.refresh()` is load-bearing and
> non-obvious. Removing items from the **addon** keyconfig does not touch the
> resolved **user** keyconfig, which is a cached merge: measured 8 addon items
> → 0 while the user keymap still listed all 8, so R stayed shadowed. With
> `wm.keyconfigs.update()` the user count drops to 0 immediately, and back to 8
> when re-enabled.

### Swivel — pivot from a picked vertex / edge / face

New: `rotools.set_swivel` (bound to plain **V** in every RoTools tool's own
keymap) picks a mesh element under the cursor and every transform tool pivots
around it. `rotools.clear_swivel` drops it. World/Local keeps applying on top,
exactly as it does for Center and Origin — the swivel is a *pivot point*, not
an orientation, so no custom transform orientation is involved.

That last point was settled by probing rather than assumed: **`orient_type` has
no `CUSTOM` member** in 5.2 (`GLOBAL/LOCAL/NORMAL/GIMBAL/VIEW/CURSOR/PARENT`),
so a picked-face-normal frame would have needed the `orient_matrix` /
`orient_matrix_type` pair. Not needed — pivot alone is what "swivel from a set
vert/edge/face" asks for.

**`core/picking.py` deliberately does not use the dragger's snapping engine.**
The BVH in `core/snapping.py` is triangulated, so its "edges" include
triangulation diagonals that do not exist in the mesh the user is looking at;
snapping a deliberately picked edge onto an invisible diagonal is indefensible.
Instead the picker takes the face index from `scene.ray_cast` and reads that
polygon off the evaluated mesh, so an n-gon's four real edges are the four
candidates.

> Verified: `scene.ray_cast` returns the **original** object but a
> `location`/`normal`/`index` belonging to the **evaluated** object's mesh. A
> subdivided cube raycast down Z reported index 20 of the evaluated mesh's 24
> polygons, and that polygon's corners contained the hit point. So the lookup
> must go through `evaluated_get(depsgraph)`; using `obj.data` would index the
> wrong mesh entirely.

AUTO mode takes vertex, then edge, then face, each only within the soft-snap
pixel margin, so it degrades to the face out in the middle of one. Verified on
a default cube: cursor near a corner → `VERTEX (1,1,1)`, near an edge midpoint
→ `EDGE (0,1,1)`, mid-face → `FACE (0,0,1)`, empty space → `None`.

Face normals are transformed by the **inverse transpose**, not the matrix —
Roblox-style building scales axes freely and the plain matrix would skew them.

The marker and the live pick preview are drawn by `ui/overlay.py`, a single
`POST_VIEW` handler, using `POLYLINE_UNIFORM_COLOR` (`viewportSize`,
`lineWidth`, `color`) and `POINT_UNIFORM_COLOR` (`color`, `size`) — uniform
names taken from the 5.2 reference, not guessed. It draws with depth test off,
like the 3D cursor: a pivot you cannot see because it is inside the part is
worse than one floating over it. Cross arms are sized through
`pixels_to_world`, per this project's no-flat-world-space-thresholds rule.

### Dragger QoL

- **R** spins the selection 90° about the drop surface's normal (world +Z when
  free-dragging). **T** tips it onto the next of its six faces. Both are
  modelled as "which of the object's six signed local axes is the resting one"
  plus "how many quarter turns about the normal", which keeps the flush
  placement exact — the depth solve already runs on the final rotation.
  `_signed_axes` sorts the six by world Z so index 0 is the axis it is already
  resting on, preserving the previous behaviour when neither key is pressed.
- **T implies alignment even when the Surface Align toggle is off.** Tipping is
  a request to put a different face against the surface; refusing to align it
  would make the key do nothing.
- **Ctrl+D** stamps a copy and keeps dragging the original. Full copies (what
  Ctrl+D means everywhere else in Blender), already coincident because
  `obj.copy()` carries the transform, with internal parents re-pointed at the
  copies so the stamp is self-contained rather than hanging off parts still
  being dragged. Cancelling the drag removes the stamps *and* the meshes they
  orphaned. Verified end to end: 2 objects in, child copy parented to the
  parent copy, data actually copied, discard freed both objects and both
  meshes.
- The header readout now carries the reference point's XYZ alongside the snap
  kind, plus spin/tip/stamp state.
- The Select tool's Soft Snap toggle is greyed while Grid is on, because
  `resolve_snap` takes the grid outright — the toggle was previously drawn as
  though the two were peers.

### Still open

- **The installed addon is not the repo.** Blender loads `roblox_tools` from
  `%APPDATA%/Blender Foundation/Blender/5.2/scripts/addons/roblox_tools/`,
  which is a **copy**, and that copy is a pre-dragger snapshot — no `drag.py`,
  `snapping.py` or `view_math.py` at all. The note in the 2026-08-24 entry
  saying the addon "is enabled directly from the repo path" is wrong. All
  verification above was done by disabling the installed copy
  (`default_set=False`), purging `sys.modules` **after** disabling, and
  importing from the repo on `sys.path`. Nothing in the install was touched.
- `roblox_tools.zip` is still stale, now more so.
- `GIZMO_GT_arrow_3d` in `'NORMAL'` draw style renders a stem, a box part-way
  along, and a cone at the tip — three glyphs per handle, so the six-arrow Move
  gizmo is busier than Studio's six clean cones. Blender's own Move tool gizmo
  draws box handles too, so this is stock styling rather than a regression, and
  `draw_style`'s full enum could not be read (`draw_style` is a dynamic
  property, absent from `gz.bl_rna.properties`, and a probe GizmoGroup's
  `setup()` never fired). Left alone rather than guessed at.

## 2026-08-25 — `docs/` folder added

Deep read of the whole addon, written up as a 12-file `docs/` folder. This file
stays the *chronological* log; `docs/` is the *structured* view. See
[docs/README.md](docs/README.md) for the index.

Four API questions were settled by probing the live Blender (5.2.0 LTS) rather
than assumed; all four are recorded in `docs/09-blender-api-notes.md`:

- **`obj.bound_box` already reflects modifier-evaluated bounds.** A plane with
  a 4-unit Solidify reported Z −2…2 on the *original* object's `bound_box`,
  matching both `evaluated_get(dg).bound_box` and the evaluated mesh's vertex
  range. This matters because the dragger's broad phase reads `bound_box` while
  its narrow phase builds the BVH from the evaluated mesh — reading the code
  suggested they could disagree and the broad phase could reject a hittable
  object. **They agree.** Not a bug; do not "fix" it.
- **An EMPTY's `bound_box` is eight zero vectors** in 5.2, not the `-1.0` the
  docs mention for "not available". So a selected Empty contributes exactly its
  origin to any `local_aabb`. `drag.py` filters Empties out; `pivot.py` and the
  gizmos do not.
- **`Matrix.normalized()` is column normalization and does not orthogonalize.**
  A shear matrix's normalized columns still had dot 0.447. So
  `local_basis_matrix` gives unit-length but not necessarily perpendicular axes
  for a sheared object.
- **Keymap shadowing is real and same-keymap.** Enumerating the resolved user
  keyconfig shows `rotools.switch_tool` ordered *ahead of* `transform.rotate`
  (R) and `object.subdivision_set` (Ctrl+1..4) inside `Object Mode`. Pressing R
  in Object Mode no longer starts a rotate.

Gaps found and **left alone** (noticed, not fixed), full list in
`docs/11-known-gaps.md`:

- `roblox_tools.zip` is stale — built 2026-08-23, so it is missing
  `snapping.py`, `view_math.py`, and `drag.py` entirely, with 9 more files
  differing. Installing from it yields an addon with no dragger.
- `CLAUDE.md`'s Layout section lists a `ui/` package that does not exist in the
  working tree (the stale zip has an empty `ui/` entry, so it once did). All UI
  is `draw_settings`; there is no `bpy.types.Panel` in the addon.
- `dragger-addon-priorities.md`, cited as the source for Tiers 0–6, is not in
  the repo.
- The 15° rotate increment is re-applied to every scene on *every* addon
  enable and never restored on unregister — stronger than "set a default".
- Scale tool's `bl_description` still promises "plane handles"; there are six
  single-axis handles and no plane handles.

## 2026-08-24 — Roblox-style dragger, Tiers 0–2

Built from `dragger-addon-priorities.md`. Scope this pass was Tiers 0–2 only
(the raycast + BVH + reference-point engine). Tiers 3–6 — modal key layer,
`blf`/`gpu` HUD, animated tilt, per-object collidable filtering — are
deliberately **not** started.

**The dragger is the Select tool, not a new tool.** Confirmed with the user:
in Roblox Studio the Select tool doubles as the dragger, so dragging a part
moves it and dragging empty space box-selects. The priorities doc had assumed
an additive standalone tool; that assumption was wrong and the doc's Tier 0
bullet ("new modal operator") was kept, but wired into `rotools.select`
rather than given its own ToolDef.

- `rotools.select` gained an `allow_drag` bool property, default **False**.
  Move/Scale/Rotate bind the same operator for plain click-select, and a body
  drag there would fight their gizmos. Only `select_tool.py` passes it True,
  via the `bl_keymap` third element: `{"properties": [("allow_drag", True)]}`.
  That format is asserted as a *list of tuples* in Blender's own
  `bl_keymap_utils/io.py:_init_properties_from_data` — a dict silently fails.
- `select.py` raycasts once on mouse-down to decide *up front* whether the
  drag threshold routes to the dragger or to box-select. `drag.py` re-raycasts
  in its own `invoke`, so it stays independently invokable. Two raycasts, but
  only on drag start, never per frame.

**Why the per-frame drop target can't use `scene.ray_cast`:** it has no way to
exclude objects, and the dragged geometry is exactly what's under the cursor.
Hence `core/snapping.py:DragScene`, which owns per-object `BVHTree`s. The
mouse-down grab raycast *does* use `scene.ray_cast` — nothing to exclude yet.

- BVH trees are built in **world space** from the evaluated mesh, lazily, and
  cached for the lifetime of one drag. Valid because nothing but the dragged
  objects moves during a drag. World space means the hot loop does no matrix
  conversion, and a BVH face index maps straight back to that triangle's three
  world corners — which is what makes the coarse→fine handoff cheap: one
  `find_nearest` per object yields the face hit *and* its vertices/edge
  midpoints.
- The synthetic ground is an **analytic infinite Z-up plane**, not a mesh quad.
  A finite baseplate stand-in would have edges you could slide off; the
  analytic version means the dragger always has something to land on. It has
  no vertices, so it participates in face/grid snapping only.

**Placement formula** (`drag.py:_apply`), the part worth not re-deriving:
with corner offsets `o` taken relative to the grab point and a surface normal
`n`, let `d = min((rot @ o)·n)`. Then `position = surface.point - n*d` rests
the box flush — only the normal component moves, so the grab point stays under
the cursor. Applied as one rigid transform
`Translation(position) @ rot @ Translation(-grab_point)` on top of each
object's *start* matrix, which preserves per-object scale and relative offsets.
Verified in-Blender: grabbing a cube by its **top** face still rests its
**bottom** on the surface (the grab point must not become the resting point).

- Surface align swings the object's **resting axis** (the local axis nearest
  world +Z at grab time, `_resting_axis`) onto the new normal — not the clicked
  face's normal. That's what makes a part dragged off the floor onto a wall tip
  over and lie against it. Alt overrides, per Tier 2.
- Snap priority is vertex > edge > face > grid. Soft geometry snapping is
  checked first and wins outright inside the margin; the grid is the fallback
  so open-space drags still land on round numbers. Reconciles the doc's two
  statements ("soft snap when hard snap is off" vs "grid fallback").
- **All pixel thresholds go through `core/view_math.py:pixels_to_world`.** The
  conversion is derived from `window_matrix[1][1]` (= 1/tan(fovy/2) perspective,
  2/view_height ortho), not tuned by eye — one pixel spans
  `2*depth / (m11 * region.height)` world units, depth pinned to 1 for ortho.
  Do not hardcode a flat world-space margin anywhere.

**Hard grid snap now outranks soft snap** (`resolve_snap`), reversing the first
pass. Reported symptom: increment set to 1, but dragged parts landing hundredths
off — a screenshot showed `Location X -1.06, Y -0.03` with Soft Snap enabled.
Cause: soft snap was checked first, so any vertex/edge/face within the margin
won and dragged the result to that neighbour's arbitrary position. Reproduced
exactly with a neighbour cube parked at `(1.06, 0.03, 1.0)`: the reference point
snapped to its vertex at `(0.06, -0.97, 0)` instead of the grid's `(0, -1, 0)`.

The priorities doc contains both "soft snap ... *when hard snap is off*" and
"vertex > edge > face > grid fallback". The first pass reconciled these by
letting geometry always win; that was the wrong call — an increment that
silently loses to a nearby vertex is not an increment. Now: grid on → grid
only, exact. Grid off → soft pass, with vertex > edge > face preserved *within*
it. Z still comes from the flush-placement step, not from snapping, which is
why Z read as an exact `1 m` even while X/Y were off.

**Modifier keys** (Tier 3's shift-hold, pulled forward because the tool felt
inert without it): Shift flips snap-enabled for as long as it is held — a
per-frame local flag, never written back to the scene toggles, per the doc.
Alt keeps the original orientation (Tier 2). Ctrl is deliberately **unbound**:
the doc's only Ctrl binding is Ctrl+D stamping, which is still unbuilt, and
there was no verified Roblox meaning for plain Ctrl to copy.

- `_modifiers(event)` exists because `event.shift` still reads True on the
  LEFT_SHIFT *release* that turns it off. On a shift/alt event, `event.value`
  is the authority. Do not read `event.shift` directly in `_apply`.
- `modal` re-applies on modifier press/release as well as MOUSEMOVE, so the
  part updates the instant Shift goes down rather than on the next nudge.

**Status bar / header.** `workspace.status_text_set` accepts a *callable*
(`fn(self, context)` with a real `self.layout`), which is what allows the
EVENT_*/MOUSE_* icons Blender's own modal tools use — a plain string gets no
icons. Both the status text and `area.header_text_set` must be cleared on
FINISHED *and* CANCELLED or the hints stay on screen after the drag ends.

**Gotcha — reloading this addon during a session.** It's enabled directly from
the repo path, so edits are live, but `del sys.modules["roblox_tools.*"]`
*before* `addon_disable` orphans the module and unregister silently no-ops
("addon_utils.disable: roblox_tools not enabled"). The `WorkSpaceTool`
subclasses then survive and the next enable dies with "Tool
'rotools.select_tool' already exists!". Fix: disable **first**, then purge
`sys.modules`. To recover once stuck, unregister the strays by walking
`bpy.types.WorkSpaceTool.__subclasses__()` for `bl_idname` starting `rotools.`.

Verified against Blender 5.2.0 LTS / Python 3.13 (the version actually running
this addon — `__pycache__` tags are `cpython-313`).

**Snap offsets are constrained to the drop surface's tangent plane** — the
single least obvious line in `drag.py:_apply`, and load-bearing. The placement
step puts the box exactly flush; applying a raw 3D snap offset on top of that
undoes it. Measured before the constraint went in, on a 1×1×1 cube dropped on a
slab whose top face is at z=0.5:

  - vertex snap toward a vertex just under the surface → box bottom driven to
    **z=0.1**, i.e. 0.4 units *sunk into the slab*
  - grid snap → box bottom to **z=0.0**, because rounding pulled Z to a round
    number and lifted/dropped the box off its surface

Projecting the offset onto the tangent plane (`offset -= normal *
offset.dot(normal)`) fixes both: the box still slides in X/Y toward the snap
target and the reported snap kind is unchanged, but flush contact is now an
invariant that snapping cannot break. Do not "simplify" this back to
`position += snap.point - reference`.

This is also *why* FACE is safe to keep in `SNAP_PRIORITY` as the doc
specifies: the offset to the nearest point on the surface being rested on is
purely along the normal, so the projection leaves exactly zero. FACE is a
principled no-op rather than the hazard it was. Free-drag (no surface hit) has
no tangent plane, so its snapping stays unconstrained 3D — correct, since there
is no flush placement to preserve.

## 2026-08-23 — Notes file created

- Established `CLAUDE.md` with a strict no-guessing rule and scope-discipline
  rules for this repo.
- Addon structure at time of writing: `core/`, `gizmos/`, `operators/`,
  `tools/`, `ui/`, registered via a `MODULES` tuple in
  `roblox_tools/__init__.py` (register/unregister loop pattern).
- No prior notes exist yet — add entries here going forward whenever a
  non-obvious decision is made, a bug's root cause is found, or work is
  left unfinished.
