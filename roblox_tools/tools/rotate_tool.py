import bpy
from bpy.types import WorkSpaceTool

from ..ui.tool_ui import draw_orientation_row, draw_snap_row, draw_swivel_row


class ROTOOLS_WT_rotate(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'

    bl_idname = "rotools.rotate_tool"
    bl_label = "Roblox Rotate"
    bl_description = (
        "Rotate objects like Roblox Studio (drag a ring to rotate around that "
        "axis, in 15 degree steps by default)"
    )
    bl_icon = "ops.transform.rotate"
    bl_widget = "ROTOOLS_GGT_rotate"
    bl_keymap = (
        ("rotools.select", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
        ("rotools.toggle_orientation", {"type": 'L', "value": 'PRESS', "ctrl": True}, None),
        ("rotools.cycle_pivot", {"type": 'L', "value": 'PRESS', "ctrl": True, "shift": True}, None),
        ("rotools.set_swivel", {"type": 'V', "value": 'PRESS'}, None),
        ("rotools.duplicate", {"type": 'D', "value": 'PRESS', "ctrl": True}, None),
    )

    def draw_settings(context, layout, tool):
        draw_orientation_row(context, layout)
        draw_swivel_row(context, layout)
        draw_snap_row(context, layout, "rotools_snap_rotate", elements=False)


def register():
    bpy.utils.register_tool(ROTOOLS_WT_rotate, after={"rotools.scale_tool"})


def unregister():
    bpy.utils.unregister_tool(ROTOOLS_WT_rotate)
