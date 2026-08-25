import bpy
from bpy.types import WorkSpaceTool

from ..ui.tool_ui import draw_orientation_row, draw_snap_row


class ROTOOLS_WT_move(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'

    bl_idname = "rotools.move_tool"
    bl_label = "Roblox Move"
    bl_description = (
        "Move objects like Roblox Studio (push one of the six arrows sitting on "
        "the part's faces, or drag the centre ring for a free move)"
    )
    bl_icon = "ops.transform.translate"
    bl_widget = "ROTOOLS_GGT_move"
    bl_keymap = (
        ("rotools.select", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
        ("rotools.toggle_orientation", {"type": 'L', "value": 'PRESS', "ctrl": True}, None),
        ("rotools.cycle_pivot", {"type": 'L', "value": 'PRESS', "ctrl": True, "shift": True}, None),
        # Plain V is unbound in Object Mode and the 3D View keymap (only Ctrl+V
        # is taken, by view3d.pastebuffer), and a tool keymap only applies while
        # that tool is active, so this shadows nothing.
        ("rotools.set_swivel", {"type": 'V', "value": 'PRESS'}, None),
    )

    def draw_settings(context, layout, tool):
        draw_orientation_row(context, layout)
        draw_snap_row(context, layout, "rotools_snap_move")


def register():
    bpy.utils.register_tool(ROTOOLS_WT_move, after={"rotools.select_tool"})


def unregister():
    bpy.utils.unregister_tool(ROTOOLS_WT_move)
