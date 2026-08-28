# 🛠️ RoTools — Bring Roblox Studio's Move/Scale/Rotate Tools into Blender

If you've ever built in **Roblox Studio** and then jumped into **Blender**, you know the tools just feel *different*. Studio's Select, Move, Scale, and Rotate tools have their own snappy, satisfying feel — and RoTools brings that exact feel into Blender's viewport.

---

## ✨ What It Does

RoTools adds **four familiar tools** to Blender's toolbar that behave just like their Roblox Studio counterparts, all working in **Edit Mode** on vertex/edge/face selections too, not just whole objects:

- 🖱️ **Select Tool** — click to select, drag empty space to box-select, and drag a part to actually *pick it up and slide it around* (just like Studio!)
- ↔️ **Move Tool** — the classic three-arrow move handles you already know
- 📦 **Scale Tool** — six handles on the box faces for resizing
- 🔄 **Rotate Tool** — three dial rings sized right to your selection

They sit **alongside** Blender's normal tools — nothing gets replaced or broken. You can switch back and forth whenever you like.

---

## 🎯 Why It Feels Like Studio (Not Just Looks Like It)

This isn't just a reskin — the *behavior* is rebuilt to match Studio's logic:

- **Dragging = moving.** In Studio, there's no separate "drag tool" — your Select tool doubles as a mover. RoTools does the same: drag a part and it slides.
- **Parts land flush on surfaces.** No clipping through the floor, no awkward floating gaps — objects rest naturally wherever you drop them, and can even tip over to lean against walls.
- **Scaling grows from the far side.** Just like Studio, dragging a scale handle stretches the part outward from the opposite face instead of puffing it up from the center.
- **Snapping that feels right out of the box.** 1-stud grid snapping and 15° rotation snapping are on by default, just like Studio.
- **One shared pivot and orientation.** Center / Origin / Swivel and World / Local aren't per-tool settings — set one, and every tool respects it, matching Studio's single toggle.
- **Non-collidable parts, just like Studio's `CanCollide`.** Add a `Collidable` custom Boolean property to an object (Object Properties ▸ Custom Properties ▸ New) and set it to unchecked to make the dragger pass straight through it — no addon UI needed, it's plain Blender.

---

## 📥 Installation

1. Grab the latest zip from the [Releases page](https://github.com/DevelopmentStatus/Rotools/releases/latest).
2. In Blender: **Edit ▸ Preferences ▸ Add-ons ▸ Install...**, and pick the zip you just downloaded.
3. Enable the checkbox next to **"RoTools - Roblox Studio Style Tools"**.
4. The four tools appear in the 3D Viewport toolbar, after Blender's own Select Box tool.

Requires **Blender 4.0+** (built and verified on 5.2.0 LTS — see [Compatibility](#-compatibility) below).

---

## ⌨️ Handy Shortcuts

- `Ctrl + 1 / 2 / 3 / 4` — quick-switch between Select / Move / Scale / Rotate
- `Ctrl + D` — duplicate the selection, Studio-style
- `Ctrl + L` — toggle between Global and Local orientation
- `Ctrl + Shift + L` — cycle the shared pivot mode (Center / Origin / Swivel)
- `V` (Rotate tool) — set the swivel pivot from the vertex/edge/face under the cursor
- Hold **Shift** while dragging to invert snapping
- Hold **Alt** while dragging to keep your part's current orientation

---

## ✅ What's Working Right Now

- Click, Shift-click, and Ctrl-click selection
- Box select
- Free-drag placement across surfaces
- Flush resting + surface alignment (tipping onto walls)
- An invisible "baseplate" ground plane, just like Studio
- Vertex/edge/face snapping *and* grid snapping
- Full Move / Scale / Rotate gizmos
- Global/Local orientation switching, shared across every tool
- Center / Origin / Swivel pivot modes, shared across every tool
- Ctrl+D drag-to-duplicate
- Move, Scale, and Rotate tools all working in Edit Mode (vertex/edge/face selections)
- Per-object `Collidable` toggle so the dragger can pass through a part

---

## 🧩 Compatibility

- Built and tested on **Blender 5.2.0 LTS**
- Declared compatible down to Blender 4.0, though that hasn't been verified yet
- Object Mode: all four tools. Edit Mesh: Move, Scale, and Rotate (Select stays Object Mode only)

---

## 📚 Full Documentation

This page is the pitch. For the technical reference — architecture, module-by-module breakdowns, the snapping/dragger internals, settings reference, and known gaps — see **[docs/README.md](docs/README.md)**.

It's still early days (version `0.3.0`), so feedback, bug reports, and feature requests are very welcome!
