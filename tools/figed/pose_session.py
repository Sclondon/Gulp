"""Opened with a built figure (.blend) so the user can pose it by hand: the skeleton selected, in Pose Mode, bones
drawn over the body. Save with Ctrl+S when done; `-- read <out.json>` (headless) then writes the pose out.

    blender work/brother_pose.blend --python tools/figed/pose_session.py
    blender -b work/brother_pose.blend --python tools/figed/pose_session.py -- read work/brother_pose.json
"""
import json
import sys

import bpy

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

if argv[:1] == ["read"]:
    out = {}
    for b in arm.pose.bones:
        q = b.matrix_basis.to_quaternion()
        loc = b.matrix_basis.to_translation()
        if abs(q.w) < 0.99999 or loc.length > 1e-5:
            rest = b.bone.matrix_local.to_3x3()         # the same turn about the bone's head in the model's own axes:
            turn = rest @ b.matrix_basis.to_3x3() @ rest.inverted()   # what a spec's "pose" takes for a bone
            out[b.name] = {"quat": [round(v, 5) for v in q], "loc": [round(v, 5) for v in loc],
                           "turn": [[round(v, 6) for v in row] for row in turn]}
    with open(argv[1], "w") as f:
        json.dump(out, f, indent=1)
    print("posed bones:", len(out), sorted(out))
else:
    def setup():
        for o in bpy.data.objects:
            o.select_set(False)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        arm.show_in_front = True
        arm.data.display_type = "STICK"
        for b in arm.pose.bones:
            b.rotation_mode = "QUATERNION"
        bpy.ops.object.mode_set(mode="POSE")
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces[0].shading.type = "SOLID"
                with bpy.context.temp_override(area=area, region=next(r for r in area.regions if r.type == "WINDOW")):
                    bpy.ops.view3d.view_axis(type="FRONT")
                    bpy.ops.view3d.view_all()
        return None

    bpy.app.timers.register(setup, first_interval=0.5)
