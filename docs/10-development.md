# 10. Development

## Repository layout

```
RoTools/
├── CLAUDE.md              project rules (no-guessing, scope discipline)
├── PROJECT_NOTES.md       chronological decision log, newest first
├── docs/                  this folder
└── roblox_tools/          the addon package
```

There is no packaged build in the tree; `roblox_tools.zip` was deleted
2026-08-25 because it had gone stale. See §10.5 to build one on demand.

There is **no git repository** here (`CLAUDE.md` notes this explicitly). That
is why `PROJECT_NOTES.md` is treated as the project's persistent memory, and
why this folder documents rationale as well as structure.

## 10.1 Installing

Blender's addons directory holds a **directory junction** to this repo:

```
%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\roblox_tools
    -> A:\gameassets\Blender\RoTools\roblox_tools
```

created with PowerShell:

```powershell
New-Item -ItemType Junction -Path "$env:APPDATA\Blender Foundation\Blender\5.2\scripts\addons\roblox_tools" -Target "A:\gameassets\Blender\RoTools\roblox_tools"
```

A **junction**, not a symlink: on Windows a junction needs neither elevation
nor Developer Mode, and it works across local volumes (A: → C:). Blender
follows it transparently.

So edits to `roblox_tools/*.py` are live — no reinstall step — but they still
need the reload dance in §10.2 to take effect in a running Blender.

> ⚠️ Before 2026-08-25 this was a **plain copy**, and it had drifted to a
> pre-dragger snapshot with no `drag.py`, `snapping.py`, or `view_math.py`.
> Anything that "verified" behaviour in Blender before that date may have been
> testing code that is not in this repo. Check `Get-Item <path>).LinkType` if
> you are ever unsure which you have.

Then enable **"RoTools - Roblox Studio Style Tools"** in Preferences ▸ Add-ons.

Once enabled, the four tools appear in the 3D Viewport toolbar in Object Mode,
after `builtin.select_box` and behind a separator.

## 10.2 Reloading during a session — the order matters

> **Gotcha.** `del sys.modules["roblox_tools.*"]` **before** `addon_disable`
> orphans the module: `unregister()` silently no-ops with
> `addon_utils.disable: roblox_tools not enabled`. The `WorkSpaceTool`
> subclasses then survive, and the next enable dies with
> `Tool 'rotools.select_tool' already exists!`.

**Correct order — disable first, then purge:**

```python
import bpy, sys, addon_utils

addon_utils.disable("roblox_tools", default_set=False)

for name in [m for m in sys.modules if m.startswith("roblox_tools")]:
    del sys.modules[name]

addon_utils.enable("roblox_tools", default_set=False)
```

### Recovering from a stuck registration

If you already hit `Tool '...' already exists!`, the stray `WorkSpaceTool`
subclasses are still registered. Walk them and unregister the RoTools ones:

```python
import bpy

for cls in list(bpy.types.WorkSpaceTool.__subclasses__()):
    if getattr(cls, "bl_idname", "").startswith("rotools."):
        try:
            bpy.utils.unregister_tool(cls)
        except Exception as exc:
            print("could not unregister", cls.bl_idname, exc)
```

Then retry the enable.

## 10.3 Adding a new module

`CLAUDE.md` is normative here: **match the existing register/unregister +
`MODULES` tuple pattern**; do not invent a different registration mechanism.

1. Create the module under the right package — `core/`, `gizmos/`,
   `operators/`, or `tools/`.
2. Give it exactly `register()` and `unregister()` at module level.
3. Import it in `roblox_tools/__init__.py` and add it to `MODULES` **at the
   right position** — see the ordering constraints in
   [02-architecture.md](02-architecture.md#registration-lifecycle). In short:
   preferences → scene properties → operators → gizmos → tools → keymaps.
4. If it changes a module's purpose or public API, update that module's
   top-of-file docstring rather than leaving it stale.
5. Log the decision in `PROJECT_NOTES.md`.

### Rules that bite

- **Every pixel threshold goes through `core/view_math.py:pixels_to_world`.**
  Never hardcode a flat world-space margin. A margin that feels right at one
  zoom level is wrong at every other one.
- **Don't add error handling for cases Blender's API guarantees can't occur.**
  (`CLAUDE.md`.)
- **Don't guess at API behaviour.** Look it up in the bundled RST docs, or
  probe it in a live session, and record the answer in
  [09-blender-api-notes.md](09-blender-api-notes.md).

## 10.4 Verifying a change

There is no automated test suite. Verification is done by running code in a
connected Blender session. The pattern used throughout these docs:

1. Build the probe in a **throwaway scene** or with objects you create and
   remove, so the user's scene is never modified.
2. Assert the actual numbers, not a visual impression — the flush-placement and
   tangent-plane behaviours were both caught by reading back coordinates.
3. Clean up in a `finally:` block and confirm no leftovers.

`core/snapping.py`, `core/bounds.py`, and `core/view_math.py` have **no
`bpy.ops` dependency**, so they are the parts most amenable to direct testing
if a suite is ever added. `core/bounds.py` needs only `mathutils` plus objects
exposing `matrix_world` and `bound_box`.

### Manual smoke checks for the dragger

The behaviours most likely to regress, and the observation that catches each:

| Behaviour | Check |
| --- | --- |
| Flush placement | Grab a cube by its **top** face — its **bottom** must still rest on the surface |
| Grab point tracking | The point you clicked stays under the cursor while dragging |
| Surface align | Drag a part from the floor onto a wall — it should tip over and lie against it |
| Alt override | Same drag with Alt held — orientation unchanged, still resting on the wall |
| Grid exactness | Grid on at 1.0 — the reported X/Y must be exact integers, not `-1.06` |
| Tangent constraint | Drop on a slab with a neighbour cube nearby — the part must not sink into or lift off the slab |
| Shift inversion | Shift with defaults on = free placement; Shift with both off = grid |
| Status cleanup | Cancel with ESC — status bar and header hints must both clear |

## 10.5 Packaging

There is no packaged build in the tree. `roblox_tools.zip` used to sit at the
repository root; it was deleted 2026-08-25 because it had gone stale — built
2026-08-23, so it shipped an addon with **no dragger at all** (`snapping.py`,
`view_math.py` and `drag.py` were missing outright, and nine more files
differed). A build artifact maintained by hand alongside a live junction is a
trap.

To build one when it is actually needed, excluding `__pycache__`:

```bash
cd A:/gameassets/Blender/RoTools && rm -f roblox_tools.zip && zip -r roblox_tools.zip roblox_tools -x '*__pycache__*'
```

`shutil.make_archive` is the obvious alternative but has no exclude hook, so it
sweeps `__pycache__/*.pyc` in.

## 10.6 Verified environment

| | |
| --- | --- |
| Blender | 5.2.0 LTS |
| Python | 3.13 (`__pycache__` tags read `cpython-313`) |
| Platform | Windows 11 |
| `bl_info["blender"]` | `(4, 0, 0)` — declared, **not** tested |

## 10.7 Documentation duties

From `CLAUDE.md`, treated as the project's memory in the absence of git
history:

- Log notable decisions, gotchas, and in-progress work in
  **`PROJECT_NOTES.md`** as you go — why something was built a particular way,
  known limitations, things tried and rejected. Newest entries at the top.
- Keep **`CLAUDE.md`** updated if project-wide rules or the module layout
  change. (It is currently out of date — see
  [11-known-gaps.md](11-known-gaps.md).)
- Update a module's top docstring when its purpose or public API changes
  meaningfully.
- Keep **this folder** in step: [09-blender-api-notes.md](09-blender-api-notes.md)
  for a newly established API fact, [11-known-gaps.md](11-known-gaps.md) when a
  gap opens or closes, and the relevant chapter when behaviour changes.
