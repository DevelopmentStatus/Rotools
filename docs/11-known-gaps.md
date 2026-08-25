# 11. Known Gaps and Sharp Edges

Everything here was found by reading the current source or probing a live
Blender. Nothing in this file has been changed unasked — per `CLAUDE.md`,
noticing an unrelated problem means mentioning it, not fixing it.

Last revised 2026-08-25, after the tool-comparison pass. §11.6 lists what that
pass **closed**, so this file is not read as a to-do list that has already been
done.

---

## 11.1 Stale artifacts

### The Blender install used to be a stale copy — now a junction

Blender loads `roblox_tools` from
`%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\roblox_tools`. Until
2026-08-25 that was a **plain copy**, and it had drifted to a pre-dragger
snapshot: no `operators/drag.py`, no `core/snapping.py`, no `core/view_math.py`
at all. Editing the repo did nothing to the running addon, and any in-Blender
verification silently tested old code.

It is now a **Windows directory junction** pointing at the repo, so repo edits
are live. A junction rather than a symlink because it needs no elevation or
Developer Mode and works across local volumes.

*Still true:* edits need an addon reload to take effect — see
[10-development.md](10-development.md) for the disable-then-purge order.

*Impact:* was high, now closed. The old copy is parked in this session's
scratchpad if anything needs recovering from it.

### `roblox_tools.zip` — deleted

The archive was a 2026-08-23 build, missing the dragger entirely. Deleted
2026-08-25 rather than maintained by hand. There is currently **no packaging
artifact**; see [10-development.md](10-development.md) for how to build one on
demand.

### `dragger-addon-priorities.md` is still not in the repo

The 2026-08-24 `PROJECT_NOTES.md` entry opens "Built from
`dragger-addon-priorities.md`", and the tier numbering (Tiers 0–6) and several
design rules are attributed to it. That file is not present anywhere in the
repository.

The notes quote enough of it that the decisions remain traceable, but the
source of truth for the unbuilt tiers is missing.

---

## 11.2 Unbuilt work

| Tier | Feature | Status |
| --- | --- | --- |
| 3 | `Ctrl+D` drag-stamp duplication | **Built** 2026-08-25 |
| 4 | `blf` / `gpu` on-canvas HUD | Not started. The status bar + area header carry the readout instead. `ui/overlay.py` now does `gpu` drawing for the swivel marker, so the machinery exists |
| 5 | Animated tilt on surface align | Not started. The tilt is instantaneous |
| 6 | Per-object "collidable" filtering | Not started. `DragScene.candidates` takes every visible mesh |

---

## 11.3 Behavioural sharp edges

### Keymap shadowing — `R` and `Ctrl+1..4`

**Verified** against the resolved user keyconfig: RoTools' `Object Mode` items
sit ahead of Blender's own in the same keymap.

| Key | Shadows | Consequence |
| --- | --- | --- |
| `R` | `transform.rotate` | Pressing `R` in Object Mode switches to the Roblox Rotate tool instead of starting a rotate |
| `Ctrl+1` … `Ctrl+4` | `object.subdivision_set` | Subdivision-level shortcuts unavailable in Object Mode |

Edit Mode is untouched, since the addon only binds into `Object Mode`.

**Now opt-out** via the `use_tool_shortcuts` preference, which unregisters all
eight items and calls `wm.keyconfigs.update()` so the change lands immediately
rather than at the next restart.

*Impact:* medium → low. Still **on by default**, so a Blender user who installs
the addon still loses `R` until they find the preference. Whether that default
should flip is a judgement call, not a bug.

### The 15° rotate increment is not restored on unregister

`scene_state._set_default_rotate_increment` now only touches scenes still
sitting on Blender's own default (0.0872665 rad = 5°), so a user's own
increment survives an addon enable. The deferred timer is unregistered in
`unregister()`.

**Still true:** disabling the addon leaves the 15° value behind rather than
reverting to 5°, and it applies to every scene in the file rather than just the
active one.

*Impact:* low.

### Sheared objects get a non-orthogonal gizmo basis

**Verified**: `Matrix.normalized()` normalizes column *lengths* but does not
orthogonalize — a shear matrix's normalized columns retained a dot product of
0.447.

So `local_basis_matrix` produces unit-length but not necessarily perpendicular
axes for a sheared object, and `LOCAL`-mode gizmos would draw a skewed frame.

*Impact:* very low in practice — Roblox-style part editing does not produce
shear — but it is an unhandled case rather than a guaranteed-impossible one.

### The swivel does not follow the geometry it was picked on

`rotools_swivel_point` is a plain world-space coordinate. Moving, rotating, or
editing the object the point was picked from leaves the swivel where it was.

This is a deliberate simplification — tracking would mean storing an object
reference plus an element index and re-resolving it through the depsgraph every
redraw, and an element index is not stable across a mesh edit anyway. But it is
worth knowing before you pick a swivel and then drag the part.

*Impact:* low, and visible: the marker stays put, so the behaviour is at least
not hidden.

### The swivel picker needs the cursor **on** a face

`pick_element` is raycast-based. Aimed at the exact projected silhouette corner
of a mesh, the ray grazes past and returns `None` — verified on a default cube.
Aiming a little inside the silhouette picks the corner correctly.

*Impact:* low, and inherent to any raycast picker.

### `DragScene` and its caches are keyed by `obj.name`

A name collision across linked libraries would cross-contaminate a BVH cache.
Not tested either way.

---

## 11.4 Code-quality observations

### `GIZMO_GT_arrow_3d` draws three glyphs per handle

In `'NORMAL'` draw style each arrow renders a stem, a box part-way along, and a
cone at the tip. With the Move gizmo's six arrows that is eighteen glyphs where
Roblox Studio draws six clean cones.

Blender's own Move tool gizmo draws box handles too, so this is stock styling
rather than something this addon introduced. `draw_style`'s full enum could not
be read at runtime — it is a dynamic property, absent from
`gz.bl_rna.properties`, and a probe `GizmoGroup`'s `setup()` never fired under
`redraw_timer` — so alternatives were left unguessed rather than tried blind.

*Impact:* cosmetic. Worth revisiting with a live `setup()` to enumerate the
enum properly.

### The swivel overlay redraws every 3D viewport

`ui/overlay._tag_redraw` walks every window and every `VIEW_3D` area. It is
called on each pick-preview update, i.e. per mouse-move while
`rotools.set_swivel` runs.

*Impact:* very low — it only runs during the picker's modal — but it is
broader than it needs to be.

---

## 11.5 Untested claims

- **Blender 4.0 support.** `bl_info` declares `(4, 0, 0)` as the minimum;
  everything was verified on 5.2.0 LTS. `snap_angle_increment_3d` in
  particular is a relatively recent property name, and the 4.0 claim has not
  been checked. `use_snap_translate` / `_rotate` / `_scale` and
  `POINT_UNIFORM_COLOR` are further 4.0 unknowns introduced by the 2026-08-25
  pass.
- **Cross-keymap precedence** for the `Q` and `W` bindings (Object Mode vs
  Window vs 3D View). Which keymap each binding lives in was enumerated; the
  resolution rule between different keymaps was not independently confirmed.
- **No automated tests exist.** `core/snapping.py`, `core/bounds.py`,
  `core/view_math.py`, and `drag._drag_roots` / `_signed_axes` are
  `bpy.ops`-free and would be the natural place to start.

---

## 11.6 Closed by the 2026-08-25 pass

Listed so this file is not mistaken for a live backlog. Full reasoning and the
measurements behind each is in `PROJECT_NOTES.md`.

| Was | Now |
| --- | --- |
| The dragger double-transformed parented selections (child at X=22 instead of 12) | `_drag_roots` writes only unparented-within-the-selection objects |
| Rotate and Scale transformed around `transform_pivot_point`, not the drawn pivot | Both force `center_override` in every mode |
| Rotate's Snap button toggled `use_snap_rotate` with the master off — it did nothing. Scale's left `use_snap_scale` off | Three `rotools_snap_*` proxies drive the master and the mode flag together |
| `try/except Exception` around `property_unset` | Probed: it does not raise. Guard and call both gone |
| `__package__.split(".")[0]` → `bl_ext` for extension installs | One `PACKAGE = __package__.rpartition(".")[0]` |
| Preference defaults duplicated as literal fallbacks at each reader | `get_pref` falls back to the declared default |
| Amber highlight colour duplicated in all three gizmo modules | `gizmo_common.HIGHLIGHT_COLOR` + `style_handle` |
| Scale tool's `bl_description` promised non-existent "plane handles" | Rewritten |
| 15° increment overwrote the user's setting on every enable | Only applied to scenes still on Blender's default |
| The deferred timer was never cancelled | Unregistered in `unregister()` |
| Selected Empties skewed gizmo pivot and bounds | `pivot.transform_objects`, shared with the dragger |
| Rotate rings positioned from origins but sized from bounds | Both from `pivot_point` / `local_aabb` in one frame |
| Scale and Rotate hardcoded `orient_type='LOCAL'` while only Move had a control | One scene-wide `rotools_orientation`, one `orientation_frame` call |
| `CLAUDE.md` listed a `ui/` package that did not exist | `ui/` exists: `tool_ui.py` + `overlay.py` |
| An unselectable object under the press ate the click | Treated as a miss; a refused drag falls back to box-select |
| `roblox_tools.zip` shipped a dragger-less addon | Deleted |
| The Blender install was a stale copy of the repo | Directory junction |
