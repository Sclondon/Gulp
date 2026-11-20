"""figed in Blender: turn a solved Figure into a mesh with its skeleton, and take pictures of it.

    blender -b --factory-startup --python tools/figed/figed_blender.py -- look <spec.json|-> <out.png> [views...]
    blender -b --factory-startup --python tools/figed/figed_blender.py -- sliders <out dir> [spec.json]
    blender -b --factory-startup --python tools/figed/figed_blender.py -- build <spec.json> <out.glb> [out.blend]
    blender -b --factory-startup --python tools/figed/figed_blender.py -- controls <out.txt>

Views: front side back quarter face face_side face_quarter hand foot. "-" as the spec is the untouched generic human.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402

PARTS = ("body", "helper-l-eye", "helper-r-eye", "helper-upper-teeth", "helper-lower-teeth", "helper-tongue")


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


TINT = "--tint" in sys.argv                         # -- look ... --tint: the head's skin coloured apart from the neck


def build(fig, name="figure", parts=PARTS, rig=True, posed=False):
    """The figure as Blender objects: one mesh per part name's first word ("body", "helper" things as "eyes",
    "teeth", "tongue"), all on one armature. Returns (objects by name, armature or None)."""
    base = fig.base
    P, H, T = fig.to_blender()
    if posed and getattr(fig, "pose", None):       # as the drawing stands (pictures only: no skeleton then)
        import figed_fit
        turns = figed_fit.full_pose(fig.pose, base.bones, H, T)
        pieces = {}
        for side, (ear, piece) in getattr(fig, "ear_pieces", {}).items():     # the cut ears stand as the head stands
            P2 = P.copy()
            P2[ear] = piece
            pieces[side] = (ear, figed_fit.pose_points(fig, P2, H, turns)[0][ear])
        P, _ = figed_fit.pose_points(fig, P, H, turns)
        fig.ear_pieces_posed = pieces
        rig = False
    kinds = {"body": "body", "helper-l-eye": "eyes", "helper-r-eye": "eyes", "helper-upper-teeth": "teeth",
             "helper-lower-teeth": "teeth", "helper-tongue": "tongue"}
    by_kind = {}
    for group, vi, ti in base.faces:
        if group in parts:
            by_kind.setdefault(kinds.get(group, group), []).append((vi, ti))
    arm = None
    if rig:
        data = bpy.data.armatures.new(name + "_rig")
        arm = bpy.data.objects.new(name + "_rig", data)
        bpy.context.scene.collection.objects.link(arm)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        for b in base.bones:
            e = data.edit_bones.new(b)
            e.head, e.tail = Vector(H[b]), Vector(T[b])
            if (e.tail - e.head).length < 1e-4:
                e.tail = e.head + Vector((0, 0, 0.02))
            e.roll = base.rig[b].get("roll", 0.0)
        for b in base.bones:
            p = base.rig[b]["parent"]
            if p:
                data.edit_bones[b].parent = data.edit_bones[p]
        bpy.ops.object.mode_set(mode="OBJECT")
    objs = {}
    for kind, faces in by_kind.items():
        used = sorted({v for vi, _ in faces for v in vi})
        remap = {v: i for i, v in enumerate(used)}
        mesh = bpy.data.meshes.new(name + "_" + kind)
        mesh.from_pydata([tuple(P[v]) for v in used], [], [[remap[v] for v in vi] for vi, _ in faces])
        mesh.update()
        if TINT and kind == "body":                   # the face in another colour, so the jaw's edge shows
            w = base.weights[used][:, base.bones.index("head")]
            col = mesh.color_attributes.new("tint", "FLOAT_COLOR", "POINT")
            flat = np.empty((len(used), 4), dtype=np.float32)
            flat[:] = (0.62, 0.62, 0.62, 1.0)
            flat[w > 0.5] = (0.85, 0.55, 0.35, 1.0)
            col.data.foreach_set("color", flat.ravel())
            mesh.color_attributes.render_color_index = 0
            mesh.color_attributes.active_color = col
        uv = mesh.uv_layers.new(name="UVMap")
        flat = []
        for _vi, ti in faces:
            for t in ti:
                flat.extend(base.uvs[t] if t >= 0 else (0.0, 0.0))
        uv.data.foreach_set("uv", flat)
        if kind == "eyes":                            # UVs of their own: each ball seen from straight ahead fills the
            co = np.array([P[v] for v in used])       # square, so an eye picture is an iris drawn round its middle
            flat2 = np.zeros((len(mesh.loops), 2))
            for sign in (1, -1):
                part = co[:, 0] * sign > 0
                mid = co[part].mean(axis=0)
                rad = np.linalg.norm(co[part] - mid, axis=1).max()
                for lp in mesh.loops:
                    if part[lp.vertex_index]:
                        q = co[lp.vertex_index] - mid
                        flat2[lp.index] = (0.5 + q[0] / (2 * rad), 0.5 + q[2] / (2 * rad))
            uv.data.foreach_set("uv", flat2.ravel())
        for poly in mesh.polygons:
            poly.use_smooth = True
        obj = bpy.data.objects.new(name + "_" + kind, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj["figed_source"] = [int(v) for v in used]
        if arm:
            w = base.weights[used]
            for i, b in enumerate(base.bones):
                col = w[:, i]
                idx = np.nonzero(col > 1e-4)[0]
                if len(idx):
                    g = obj.vertex_groups.new(name=b)
                    for j in idx:
                        g.add([int(j)], float(col[j]), "REPLACE")
            obj.parent = arm
            m = obj.modifiers.new("rig", "ARMATURE")
            m.object = arm
        if kind == "body" and getattr(fig, "ears", None) and fig.ears.get("cut"):
            cut_ears(fig, obj, remap, P)
        objs[kind] = obj
    return objs, arm


def cut_ears(fig, obj, remap, P):
    """The ears as pieces of their own (Figure._move_ears has already smoothed the head over where they stood and
    worked out where each now stands): a copy of every face that is wholly ear, at the ear's new place."""
    import bmesh
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    made = []
    for side, (ear, piece) in (getattr(fig, "ear_pieces_posed", None) or getattr(fig, "ear_pieces", {})).items():
        at = {remap[int(i)]: piece[k] for k, i in enumerate(ear) if int(i) in remap}
        copy = {}
        count = 0
        for f in [f for f in bm.faces if all(v.index in at for v in f.verts)]:
            vs = []
            for v in f.verts:
                if v.index not in copy:
                    copy[v.index] = bm.verts.new(tuple(at[v.index]))
                vs.append(copy[v.index])
            try:
                g = bm.faces.new(vs)
            except ValueError:
                continue
            g.smooth = True
            if uv:
                for lf, lg in zip(f.loops, g.loops):
                    lg[uv].uv = lf[uv].uv
            count += 1
        # the head where the ear stood keeps the ear's faces, flattened: they must not show the ear's paint, so
        # their UVs go to the corner of plain skin that paint_project.py leaves
        if uv:
            under = {remap[int(i)] for i in fig._ear_masks()[side][0] if int(i) in remap}
            for f in bm.faces:
                if all(v.index in under for v in f.verts) and not any(v in copy.values() for v in f.verts):
                    for lp in f.loops:
                        lp[uv].uv = (0.002, 0.002)
        # the cut edge of the piece carried on INTO the head as a skirt, so no open rim shows behind the ear and
        # the ear reads as joined to the head
        own = set(copy.values())
        rim = [e for e in bm.edges if e.verts[0] in own and e.verts[1] in own and len(e.link_faces) == 1]
        inward = -1.0 if side == "l" else 1.0
        # ... closed to ONE point inside the head (a cone, hidden under the skin): a straight skirt showed behind
        # the ear as a hollow tube ("the back of his ears have some strange geomtery", the user)
        deep = {}
        if rim:
            pts = {v for e in rim for v in e.verts}
            mid = sum((v.co for v in pts), type(next(iter(pts)).co)()) / len(pts)
            apex = bm.verts.new((mid.x + inward * 0.03, mid.y, mid.z))
            deep[apex] = apex
            for e in rim:
                a_, b_ = e.verts
                try:
                    g = bm.faces.new((a_, b_, apex))
                except ValueError:
                    continue
                g.smooth = True
        made += list(copy.values()) + list(deep.values())
        print("ear %s: a piece of %d points, %d faces, a skirt of %d edges" % (side, len(copy), count, len(rim)))
    bm.verts.index_update()
    new = [v.index for v in made]
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    group = obj.vertex_groups.get("head")
    if group:
        group.add(new, 1.0, "REPLACE")


def paint_plain(objs):
    cols = {"body": (0.62, 0.62, 0.62, 1), "eyes": (0.92, 0.92, 0.9, 1), "teeth": (0.9, 0.9, 0.85, 1),
            "tongue": (0.6, 0.35, 0.35, 1)}
    for kind, obj in objs.items():
        mat = bpy.data.materials.new("plain_" + kind)
        mat.diffuse_color = cols.get(kind, (0.6, 0.6, 0.6, 1))
        obj.data.materials.append(mat)


# --- pictures --------------------------------------------------------------------------------------------------
def _scene(res):
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.display.shading.light = "STUDIO"
    s.display.shading.color_type = "VERTEX" if TINT else "MATERIAL"
    s.display.shading.show_cavity = True
    s.display.shading.cavity_type = "BOTH"
    s.display.shading.show_shadows = False
    s.display.shading.show_specular_highlight = False
    s.display.render_aa = "8"
    s.view_settings.view_transform = "Standard"
    s.render.film_transparent = False
    if s.world is None:
        s.world = bpy.data.worlds.new("w")
    s.world.color = (0.82, 0.81, 0.85)
    s.render.resolution_x, s.render.resolution_y = res
    s.render.image_settings.file_format = "PNG"
    return s


def _camera(name="figed_cam"):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    bpy.context.scene.camera = cam
    return cam


def _aim(cam, centre, direction, scale, up=None):
    d = Vector(direction).normalized()
    cam.location = Vector(centre) - d * 10.0
    if up is None:
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    else:                                             # a view with its own "up" (a hand seen fingers up)
        z = -d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        cam.rotation_euler = Matrix((x, y, z)).transposed().to_euler()
    cam.data.ortho_scale = scale
    cam.data.clip_start, cam.data.clip_end = 0.1, 40.0


def view_boxes(fig):
    """Where each named view looks: name -> (centre, direction, height seen in metres, aspect w/h)."""
    P, H, T = fig.to_blender()
    body = P[fig.base.indices("body")]
    top = body[:, 2].max()
    mid = np.array([0.0, 0.0, top / 2])
    head = np.array([0.0, H["head"][1] - 0.02, top - (top - H["head"][2]) * 0.78])
    hh = (top - H["head"][2]) * 2.3
    hand = (H["hand_l"] + T["middle_03_l"]) / 2
    foot = (H["foot_l"] + T["ball_l"]) / 2
    q = math.sqrt(0.5)
    low = np.array([0.0, 0.0, top * 0.31])
    chest = np.array([0.0, 0.0, top * 0.74])
    unit = lambda v: v / np.linalg.norm(v)
    hands = {}
    for s in ("l", "r"):                              # each hand in its own frame: fingers up, seen square on
        f = unit(T["middle_03_" + s] - H["hand_" + s])
        a = H["index_01_" + s] - H["pinky_01_" + s]
        a = unit(a - f * a.dot(f))
        n = np.cross(f, a)
        if n[2] + n[0] * (1 if s == "l" else -1) < 0: # out of the back of the hand (it faces up and out)
            n = -n
        c = H["hand_" + s] + (T["middle_03_" + s] - H["hand_" + s]) * 0.42
        hands["hand_back_" + s] = (c, tuple(-n), 0.3, 0.8, tuple(f))
        hands["hand_palm_" + s] = (c, tuple(n), 0.3, 0.8, tuple(f))
        hands["hand_edge_" + s] = (c, tuple(-a), 0.3, 0.8, tuple(f))
    return {
        **hands,
        "chest": (chest, (0, 1, 0), top * 0.42, 1.5), "chest_back": (chest, (0, -1, 0), top * 0.42, 1.5),
        "chest_side": (chest, (-1, 0, 0), top * 0.42, 0.8), "chest_quarter": (chest, (-q, q, 0), top * 0.42, 1.3),
        "chest_top": (chest, (0, 0, -1), top * 0.36, 1.8, (0, 1, 0)),
        "front": (mid, (0, 1, 0), top * 1.06, 1.0), "back": (mid, (0, -1, 0), top * 1.06, 1.0),
        "side": (mid, (-1, 0, 0), top * 1.06, 0.45), "quarter": (mid, (-q, q, 0), top * 1.06, 0.95),
        "face": (head, (0, 1, 0), hh, 0.85), "face_side": (head, (-1, 0, 0), hh, 0.85),
        "face_quarter": (head, (-q, q, 0), hh, 0.85),
        # the five views of a head sheet, in its order: face, face_quarter_r, face_side_r, face_quarter, face_back
        "face_quarter_r": (head, (q, q, 0), hh, 0.85), "face_side_r": (head, (1, 0, 0), hh, 0.85),
        "face_back": (head, (0, -1, 0), hh, 0.85),
        "legs": (low, (0, 1, 0), top * 0.66, 0.8), "legs_back": (low, (0, -1, 0), top * 0.66, 0.8),
        "legs_side": (low, (-1, 0, 0), top * 0.66, 0.55),
        "hand": (hand, (0, 1, 0), 0.34, 1.0), "foot": (foot, (-q, q, -0.4), 0.4, 1.0),
    }


def shoot(fig, out, views=("front", "side", "back", "quarter"), height_px=900, tmp=None):
    """Render the views side by side into one PNG."""
    boxes = view_boxes(fig)
    cam = _camera()
    tmp = tmp or os.path.join(os.path.dirname(out), "_figed_tmp")
    os.makedirs(tmp, exist_ok=True)
    strips = []
    for v in views:
        centre, direction, seen, aspect = boxes[v][:4]
        up = boxes[v][4] if len(boxes[v]) > 4 else None
        w = int(height_px * aspect) // 2 * 2
        s = _scene((w, height_px))
        _aim(cam, centre, direction, seen if aspect <= 1 else seen * aspect, up)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = seen
        s.render.filepath = os.path.join(tmp, v + ".png")
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(s.render.filepath)
        a = np.array(img.pixels[:]).reshape(height_px, w, 4)
        strips.append(a)
        bpy.data.images.remove(img)
    save_pixels(np.concatenate(strips, axis=1), out)


def save_pixels(a, out):
    h, w = a.shape[:2]
    img = bpy.data.images.new("out", w, h, alpha=True)
    img.pixels.foreach_set(a.astype(np.float32).ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def stack(rows, out):
    """Rows of pictures (arrays of equal width) one above another; the first row ends up on top."""
    width = max(r.shape[1] for r in rows)
    padded = []
    for r in rows:
        if r.shape[1] < width:
            pad = np.ones((r.shape[0], width - r.shape[1], 4), dtype=r.dtype)
            pad[:, :, :3] = 0.82
            r = np.concatenate([r, pad], axis=1)
        padded.append(r)
    save_pixels(np.concatenate(padded[::-1], axis=0), out)


def load_pixels(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.array(img.pixels[:]).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return a


def figure_from(base, spec_path):
    return figed.Figure(base, None if spec_path in ("-", "") else figed.load_spec(spec_path))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print(__doc__)
        return
    base = figed.Base()
    cmd = argv[0]
    if cmd == "controls":
        lines = []
        for folder in sorted({c["folder"] for c in base.controls.values()}):
            lines.append("[%s]" % folder)
            for n in base.control_names():
                c = base.controls[n]
                if c["folder"] == folder:
                    lines.append("  %-40s %s%s" % (n, "both ways" if c["neg"] else "one way",
                                                  ", left/right" if c["sides"] else ""))
        lines.append("[friendly names]")
        for k in sorted(figed.ALIASES):
            lines.append("  %-24s = %s" % (k, ", ".join(figed.ALIASES[k])))
        lines.append("[bones: <name>.length|width|depth|girth|size]")
        for k in sorted(figed.BONE_SETS):
            lines.append("  " + k)
        with open(argv[1], "w") as f:
            f.write("\n".join(lines) + "\n")
        print("controls:", len(base.controls))
    elif cmd == "look":
        reset()
        fig = figure_from(base, argv[1])
        views = [a for a in argv[3:] if not a.startswith("--")]
        objs, _arm = build(fig, rig=False, posed="--posed" in argv)
        paint_plain(objs)
        shoot(fig, argv[2], tuple(views) or ("front", "side", "back", "quarter"))
        print("measures:", {k: round(v, 3) for k, v in fig.measures().items()})
    elif cmd == "turn":                               # -- turn <spec> <frames dir> [count] [--posed]: a turnaround
        reset()
        fig = figure_from(base, argv[1])
        objs, _arm = build(fig, rig=False, posed="--posed" in argv)
        paint_plain(objs)
        count = int(argv[3]) if len(argv) > 3 and argv[3].isdigit() else 36
        centre, _d, seen, _a = view_boxes(fig)["front"][:4]
        cam = _camera()
        os.makedirs(argv[2], exist_ok=True)
        s = _scene((800, 800))
        for i in range(count):
            a = 2 * math.pi * i / count
            _aim(cam, centre, (math.sin(a), math.cos(a), 0), seen)
            cam.data.sensor_fit = "VERTICAL"
            cam.data.ortho_scale = seen
            s.render.filepath = os.path.join(argv[2], "turn_%03d.png" % i)
            bpy.ops.render.render(write_still=True)
    elif cmd == "sliders":
        out = argv[1]
        os.makedirs(out, exist_ok=True)
        spec = figed.load_spec(argv[2]) if len(argv) > 2 else {}
        demos = [
            ("generic", {}, {}),
            ("shin_length +1.5", {"shin_length": 1.5}, {}), ("shin_length -1", {"shin_length": -1}, {}),
            ("forearm_length +1.5", {"forearm_length": 1.5}, {}),
            ("finger_length +1.5", {"finger_length": 1.5}, {}),
            ("hand.width x1.4 (ours)", {}, {"hand.width": 1.4}),
            ("shoulder_width +1.5", {"shoulder_width": 1.5}, {}),
            ("chest +1.5", {"chest": 1.5}, {}), ("hips +1.5", {"hips": 1.5}, {}),
            ("thigh+calf.length x0.75 (ours)", {}, {"thigh.length": 0.75, "calf.length": 0.75}),
            ("head.size x1.25 (ours)", {}, {"head.size": 1.25}),
        ]
        rows, row = [], []
        for i, (label, t, b) in enumerate(demos):
            reset()
            s = {"macro": spec.get("macro", {}), "targets": dict(spec.get("targets", {}), **t),
                 "bones": dict(spec.get("bones", {}), **b)}
            fig = figed.Figure(base, s)
            objs, _ = build(fig, rig=False)
            paint_plain(objs)
            p = os.path.join(out, "s%02d.png" % i)
            shoot(fig, p, ("front",), 520)
            print("demo", i, label)
            row.append(load_pixels(p))
            if len(row) == 6 or i == len(demos) - 1:
                rows.append(np.concatenate(row, axis=1))
                row = []
        stack(rows, os.path.join(out, "sliders.png"))
        with open(os.path.join(out, "sliders.txt"), "w") as f:
            f.write("\n".join("%d: %s" % (i, d[0]) for i, d in enumerate(demos)))
        reset()
        rows = []
        for label, t in (("generic", {}), ("brow down+forward", {"brow_height": -1, "brow_forward": 1}),
                         ("nose bigger, wider", {"nose_size": 1, "nose_width": 1, "nostril_width": 1}),
                         ("jaw wider, chin wider", {"jaw_width": 1, "chin_width": 1}),
                         ("cheeks fuller", {"cheek_fullness": 1})):
            reset()
            fig = figed.Figure(base, {"macro": spec.get("macro", {}), "targets": t})
            objs, _ = build(fig, rig=False)
            paint_plain(objs)
            p = os.path.join(out, "f_%s.png" % label.split()[0])
            shoot(fig, p, ("face", "face_side"), 420)
            rows.append(load_pixels(p))
        save_pixels(np.concatenate(rows, axis=1), os.path.join(out, "faces.png"))
    elif cmd == "build":
        reset()
        fig = figure_from(base, argv[1])
        name = os.path.splitext(os.path.basename(argv[2]))[0]
        objs, arm = build(fig, name=name)
        paint_plain(objs)
        if len(argv) > 3:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[3]))
        bpy.ops.export_scene.gltf(filepath=os.path.abspath(argv[2]), export_format="GLB", export_yup=True,
                                  export_animations=False, export_skins=True)
        tris = sum(len(p.vertices) - 2 for o in objs.values() for p in o.data.polygons)
        print("built", argv[2], "triangles", tris, "bones", len(base.bones))


if __name__ == "__main__":
    main()
