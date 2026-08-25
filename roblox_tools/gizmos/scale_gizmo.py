"""Roblox Studio's Scale handles: six box handles on the bounding-box faces,
anchored so the part grows out of the face you drag.

The anchor is always forced with `center_override`, never left to Blender.
Leaving it unset means `transform.resize` falls back to
`tool_settings.transform_pivot_point` - MEDIAN_POINT by default, but CURSOR for
anyone who has ever used the pivot pie menu - and then the part scales around a
point nowhere near the handles that are drawn. Forcing it in every mode keeps
"what is drawn" and "what is transformed" the same thing.
"""

import bpy
from mathutils import Matrix

from ..core.bounds import AXIS_INDEX, aabb_center, local_aabb, point_from_local
from ..core.pivot import pivot_point, swivel_point, transform_objects
from ..core.gizmo_common import (
    AXIS_COLORS,
    FLIP_ROTATION,
    orientation_frame,
    style_handle,
)

HANDLE_GAP = 0.3

HANDLES = [(axis, sign) for axis in 'XYZ' for sign in (1, -1)]


class ROTOOLS_GGT_scale(bpy.types.GizmoGroup):
    bl_idname = "ROTOOLS_GGT_scale"
    bl_label = "Roblox Scale Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    # 'SCALE' makes the gizmo group respect camera zoom instead of drawing at a
    # constant on-screen size (bpy.types.GizmoGroup.bl_options).
    bl_options = {'3D', 'SCALE'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def _make_axis_gizmo(self, axis, sign):
        # GIZMO_GT_primitive_3d ('CUBE'/'PLANE') doesn't respect gz.color for its fill
        # (renders bright white regardless) - arrow_3d does, so use a short stem that
        # starts at the bounding-box face and ends HANDLE_GAP beyond it.
        gz = style_handle(self.gizmos.new("GIZMO_GT_arrow_3d"), AXIS_COLORS[axis])
        gz.draw_style = 'BOX'
        gz.length = HANDLE_GAP

        op = gz.target_set_operator("transform.resize")
        op.release_confirm = True
        op.constraint_axis = tuple(a == axis for a in 'XYZ')
        self.axis_ops[(axis, sign)] = op
        return gz

    def setup(self, context):
        self.axis_ops = {}
        self.axis_gizmos = {
            (axis, sign): self._make_axis_gizmo(axis, sign) for axis, sign in HANDLES
        }

    def draw_prepare(self, context):
        objects = transform_objects(context)
        if not objects:
            return

        rotation_3x3, axis_rotations, orient_type = orientation_frame(context)
        mins, maxs = local_aabb(objects, rotation_3x3)
        mid = aabb_center(mins, maxs)
        bounds = {1: maxs, -1: mins}

        scene = context.scene
        # A picked swivel outranks the scale anchor: setting one is an explicit
        # "work from this point", and it would be strange for it to steer Move
        # and Rotate but not Scale.
        swivel = swivel_point(scene) if scene.rotools_pivot_mode == 'SWIVEL' else None
        use_opposite_face = swivel is None and scene.rotools_scale_pivot == 'OPPOSITE_FACE'
        center = pivot_point(context, rotation_3x3)

        # Handle stems start at the selection's actual bounding-box face on their side
        # (not a fixed distance from the pivot, so they track the object's real size)
        # and reach HANDLE_GAP beyond it via the arrow's own length.
        for (axis, sign), gz in self.axis_gizmos.items():
            i = AXIS_INDEX[axis]
            scalars = list(mid)
            scalars[i] = bounds[sign][i]
            handle_pos = point_from_local(rotation_3x3, *scalars)
            rot = axis_rotations[axis] if sign == 1 else axis_rotations[axis] @ FLIP_ROTATION
            gz.matrix_basis = Matrix.Translation(handle_pos) @ rot

            op = self.axis_ops[(axis, sign)]
            op.orient_type = orient_type
            if use_opposite_face:
                # Anchor at the face on the opposite side from the handle being dragged.
                anchor = list(mid)
                anchor[i] = bounds[-sign][i]
                op.center_override = point_from_local(rotation_3x3, *anchor)
            else:
                op.center_override = swivel if swivel is not None else center


def register():
    bpy.utils.register_class(ROTOOLS_GGT_scale)


def unregister():
    bpy.utils.unregister_class(ROTOOLS_GGT_scale)
