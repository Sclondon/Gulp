"""A figure opened for sculpting by hand, and the sculpt read back as a correction the editor keeps.

    blender -b --factory-startup --python tools/figed/sculpt_session.py -- make <spec.json> <work.blend> [sheet.json]
    blender <work.blend> --python tools/figed/sculpt_session.py                         (opens Sculpt Mode)
    blender -b <work.blend> --python tools/figed/sculpt_session.py -- read <out.sculpt.json> [--add <earlier.sculpt.json>]

The figure is built as it stands (all sliders and corrections, at rest, no skeleton) and its points are remembered in
the file. `read` writes how far each point of the base mesh was moved (metres, the editor's own axes) to a
`.sculpt.json`; a spec names it as `"sculpt": "<path>"` and `Figure.to_blender` adds it last. The cut-off ear pieces
are copies: sculpting them is not kept.
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

if argv[:1] == ["read"]:
    obj = next(o for o in bpy.data.objects if o.type == "MESH" and "figed_source" in o
               and "figed_rest" in o.data.attributes)
    src = list(obj["figed_source"])
    now = np.array([v.co[:] for v in obj.data.vertices])[:len(src)]
    rest = np.array([d.vector[:] for d in obj.data.attributes["figed_rest"].data])[:len(src)]
    d = now - rest
    moved = np.nonzero(np.linalg.norm(d, axis=1) > 1e-5)[0]
    add = {}
    if "--add" in argv:                                # strokes made on top of an earlier sculpt: the two summed
        with open(argv[argv.index("--add") + 1]) as f:
            old = json.load(f)
        add = {int(i): np.array(m) for i, m in zip(old["points"], old["moves"])}
    total = {int(src[i]): d[i] for i in moved}
    for i, m in add.items():
        total[i] = total.get(i, 0) + m
    with open(argv[1], "w") as f:
        json.dump({"about": "Hand sculpt read by sculpt_session.py: base point -> how far it was moved (metres).",
                   "points": sorted(total), "moves": [[round(float(x), 6) for x in total[i]] for i in sorted(total)]}, f)
    print("sculpt: %d points moved this time, furthest %.1f mm; %d in all" % (
        len(moved), 1000 * (float(np.linalg.norm(d, axis=1).max()) if len(d) else 0.0), len(total)))
    sys.exit(0)
    with open(argv[1], "w") as f:
        json.dump({"about": "Hand sculpt read by sculpt_session.py: base point -> how far it was moved (metres).",
                   "points": [int(src[i]) for i in moved],
                   "moves": [[round(float(x), 6) for x in d[i]] for i in moved]}, f)
    far = float(np.linalg.norm(d, axis=1).max()) if len(d) else 0.0
    print("sculpt: %d points moved, furthest %.1f mm" % (len(moved), 1000 * far))
elif argv[:1] == ["make"]:                             # headless: -- make <spec.json> <work.blend>
    import figed  # noqa: E402
    import figed_blender as fb  # noqa: E402

    fig = figed.Figure(figed.Base(), figed.load_spec(argv[1]))
    fb.reset()
    objs, _arm = fb.build(fig, rig=False)
    body = objs["body"]                                # no materials: plain grey, nothing for the window to trip on
    keep = body.data.attributes.new("figed_rest", "FLOAT_VECTOR", "POINT")
    keep.data.foreach_set("vector", np.array([v.co[:] for v in body.data.vertices]).ravel())
    if len(argv) > 3:                                  # a head sheet: its front and profile as see-through pictures
        import math
        import figed_fit  # noqa: E402
        with open(argv[3]) as f:
            sheet = json.load(f)
        P, _H, _T = fig.to_blender()
        base = fig.base
        skin = base.indices("body")
        head = skin[base.weights[skin, base.bones.index("head")] > 0.6]
        chin = P[figed_fit.mark_vertices(base)["chin"]]
        mid = head[np.abs(P[head][:, 0]) < 0.012]
        nose = P[mid[np.argmin(P[mid][:, 1])]]
        high = P[head][:, 2].max() - chin[2]
        img = bpy.data.images.load(os.path.abspath(sheet["picture"]))
        img.pack()
        W, Hpx = img.size
        k = W / float(sheet["box_width"])
        for v in sheet["views"]:
            if v["view"] not in ("face", "face_side_r"):
                continue
            s_ = high / ((v["chin"] - v["crown"]) * k)       # metres a pixel: crown to chin as the model's
            nx, ny = v["nose"][0] * k, v["nose"][1] * k
            e = bpy.data.objects.new("bible_front" if v["view"] == "face" else "bible_profile", None)
            bpy.context.scene.collection.objects.link(e)
            e.empty_display_type = "IMAGE"
            e.data = img
            e.empty_display_size = W * s_
            if v["view"] == "face":                    # numpad 1: across x, up z, noses together
                e.rotation_euler = (math.radians(90), 0, 0)
                e.location = (nose[0] - (nx - W / 2) * s_, 0.0, nose[2] + (ny - Hpx / 2) * s_)
            else:                                      # Ctrl + numpad 3 (he faces right): across -y, up z
                e.rotation_euler = (math.radians(90), 0, math.radians(-90))
                e.location = (0.0, nose[1] + (nx - W / 2) * s_, nose[2] + (ny - Hpx / 2) * s_)
            e.use_empty_image_alpha = True
            e.color[3] = 0.45
            e.empty_image_depth = "FRONT"
            e.show_empty_image_perspective = False
            e.show_empty_image_only_axis_aligned = True
            e.hide_select = True
    # saved already IN Sculpt Mode: entering it in the window is an undo step, and the user's first Ctrl+Z then
    # drops back to Object Mode (where G moves the whole figure)
    for o in bpy.data.objects:
        o.select_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="SCULPT")
    bpy.context.scene.tool_settings.sculpt.use_symmetry_x = True
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[2]))
    print("made", argv[2], "mode", bpy.context.mode)
else:                                                  # in a window, on a file "make" wrote: set up Sculpt Mode
    body = next(o for o in bpy.data.objects if o.type == "MESH" and "figed_rest" in o.data.attributes)

    def setup():
        for o in bpy.data.objects:
            o.select_set(False)
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        if bpy.context.mode != "SCULPT":
            bpy.ops.object.mode_set(mode="SCULPT")
        bpy.context.scene.tool_settings.sculpt.use_symmetry_x = True      # both sides of the face together
        top = max(v.co.z for v in body.data.vertices)
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                region = next(r for r in area.regions if r.type == "WINDOW")
                area.spaces[0].shading.type = "SOLID"
                with bpy.context.temp_override(area=area, region=region):
                    try:                                 # Blender 4.3: brushes are assets, not tools
                        bpy.ops.brush.asset_activate(
                            asset_library_type="ESSENTIALS",
                            relative_asset_identifier="brushes/essentials_brushes-mesh_sculpt.blend/Brush/Grab")
                    except Exception as e:
                        print("grab brush:", e)
                    bpy.ops.view3d.view_axis(type="LEFT")           # he faces right, as a head sheet's profile
                area.spaces[0].region_3d.view_perspective = "ORTHO"   # reference pictures show only straight on
                area.spaces[0].region_3d.view_location = (0.0, -0.05, top - 0.13)
                area.spaces[0].region_3d.view_distance = 0.75
        return None

    def grab():                                        # the Grab brush: only takes once the window has settled
        area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        with bpy.context.temp_override(window=bpy.context.window, area=area, region=region):
            bpy.ops.brush.asset_activate(
                asset_library_type="ESSENTIALS",
                relative_asset_identifier="brushes/essentials_brushes-mesh_sculpt.blend/Brush/Grab")
        brush = bpy.context.scene.tool_settings.sculpt.brush
        if brush:
            bpy.context.scene.tool_settings.unified_paint_settings.size = 110      # about an ear across at this zoom
            brush.strength = 1.0
        try:                                           # so the user's first Ctrl+Z cannot undo the brush itself
            with bpy.context.temp_override(window=bpy.context.window, area=area, region=region):
                bpy.ops.ed.undo_push(message="figed sculpt start")
        except Exception as e:
            print("undo push:", e)
        return None

    bpy.app.timers.register(setup, first_interval=0.8)
    bpy.app.timers.register(grab, first_interval=2.5)
