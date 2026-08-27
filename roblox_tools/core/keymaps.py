"""Global Object Mode shortcuts for switching RoTools tools.

These shadow Blender's own bindings in the same keymap - verified against the
resolved user keyconfig, `rotools.switch_tool` sorts ahead of
`object.subdivision_set` on Ctrl+1..4. That is a real cost for a Blender user,
so the whole set is behind the `use_tool_shortcuts` preference and can be
turned off without editing this file.
"""

import bpy

from .preferences import get_pref

# (letter/number key, ctrl, tool_id) -
# Ctrl+1/2/3/4 mirror Roblox Studio's exact Select/Move/Scale/Rotate shortcuts.
BINDINGS = (
    ('ONE', True, "rotools.select_tool"),
    ('TWO', True, "rotools.move_tool"),
    ('THREE', True, "rotools.scale_tool"),
    ('FOUR', True, "rotools.rotate_tool"),
)

addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is None:
        return
    if not get_pref(bpy.context, "use_tool_shortcuts"):
        return

    km = kc.keymaps.new(name="Object Mode", space_type='EMPTY')
    for key, ctrl, tool_id in BINDINGS:
        kmi = km.keymap_items.new("rotools.switch_tool", key, 'PRESS', ctrl=ctrl)
        kmi.properties.tool_id = tool_id
        addon_keymaps.append((km, kmi))


def refresh():
    """Re-apply the bindings after the preference toggling them changes.

    The `keyconfigs.update()` is load-bearing. Removing items from the *addon*
    keyconfig does not touch the resolved *user* keyconfig, which is a cached
    merge - verified in 5.2, the addon keymap went 4 items -> 0 while the user
    keymap still listed all 4, so Ctrl+1..4 stayed shadowed until Blender
    happened to rebuild. `update()` forces that rebuild, and the count drops
    to 0 at once.
    """
    unregister()
    register()
    bpy.context.window_manager.keyconfigs.update()


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
