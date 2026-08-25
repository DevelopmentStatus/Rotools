"""Addon preferences, plus the single accessor every reader goes through.

`get_pref` exists so a preference's default lives in exactly one place - the
property declaration below. Call sites used to repeat the default as a literal
fallback (`... if addon else 5`), which silently drifts the moment one of the
two is edited.
"""

import bpy

# `roblox_tools`, whether the addon is installed legacy-style (package
# `roblox_tools.core`) or as an extension (`bl_ext.<repo>.roblox_tools.core`).
# `split(".")[0]` - which this module used to do - returns `bl_ext` in the
# extension case and never finds the preferences.
PACKAGE = __package__.rpartition(".")[0]


def get_prefs(context):
    """This addon's AddonPreferences, or None when it is not registered as an addon."""
    addon = context.preferences.addons.get(PACKAGE)
    return addon.preferences if addon else None


def get_pref(context, name):
    """One preference value, falling back to its own declared default."""
    prefs = get_prefs(context)
    if prefs is None:
        return RoToolsPreferences.bl_rna.properties[name].default
    return getattr(prefs, name)


def _shortcuts_changed(self, context):
    # Imported here rather than at module scope: keymaps reads this module, so
    # a top-level import would be circular.
    from . import keymaps
    keymaps.refresh()


class RoToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = PACKAGE

    box_select_threshold: bpy.props.IntProperty(
        name="Box Select Drag Threshold (px)",
        default=5,
        min=1,
        max=50,
    )

    # A screen-space margin, not a world-space one: the dragger converts it
    # through the current view (core/view_math.pixels_to_world) so the pull
    # feels the same zoomed in as zoomed out.
    soft_snap_margin: bpy.props.IntProperty(
        name="Soft Snap Margin (px)",
        description="How close the reference point must get to a vertex or edge "
                    "midpoint before the dragger snaps onto it",
        default=12,
        min=1,
        max=100,
    )

    # Verified against the resolved user keyconfig: these items sort ahead of
    # Blender's own inside `Object Mode`, so they really do shadow them. Made
    # opt-out rather than unconditional because R is deep Blender muscle memory.
    use_tool_shortcuts: bpy.props.BoolProperty(
        name="Tool Shortcuts",
        description="Bind Q/W/E/R and Ctrl+1..4 to the RoTools tools. These shadow "
                    "Blender's own Object Mode bindings: R no longer starts a rotate, "
                    "and Ctrl+1..4 no longer set subdivision levels",
        default=True,
        update=_shortcuts_changed,
    )

    swivel_marker_size: bpy.props.IntProperty(
        name="Swivel Marker Size (px)",
        description="On-screen size of the swivel pivot marker and its axis cross",
        default=9,
        min=3,
        max=40,
    )

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.prop(self, "box_select_threshold")
        col.prop(self, "soft_snap_margin")
        col.prop(self, "swivel_marker_size")

        box = layout.box()
        box.prop(self, "use_tool_shortcuts")
        sub = box.column(align=True)
        sub.active = self.use_tool_shortcuts
        sub.label(text="Q / W / E / R  and  Ctrl+1..4  select Select / Move / Scale / Rotate", icon='INFO')
        sub.label(text="While on: R does not start transform.rotate, Ctrl+1..4 do not set subdivision levels")


def register():
    bpy.utils.register_class(RoToolsPreferences)


def unregister():
    bpy.utils.unregister_class(RoToolsPreferences)
