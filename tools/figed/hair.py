"""Hair for a figure: pieces of their own that sit on the bare head (the base model stays bald and shaven).

    blender -b --factory-startup --python tools/figed/hair.py -- <spec.json> <out.png> [--wear hair,moustache]
            [--glb <head_with_hair.glb>]

THE HAIR IS DRAWN BY THE GAME'S HAIR SHADER, NOT MODELLED (the user, 2026-11-18: "Dont try to model the beard it
should be made with a hair shader"; 2026-11-20, of a first pass here that modelled curl clumps and painted locks on
them: "Why did you do if you know I said not to for the hair?"). So this only makes the plain smooth surfaces the
shader draws on, with the texture coordinates it reads, and `tests/figed_hair_view.gd` shows them in Godot wearing
`shaders/ink/hair_ink.gdshader`. The pictures this script renders itself are plain colour: shape only.

- `hair`: the scalp's own faces inside a hairline rule (written from the eyes, the crown and the angle round the
  head, so it follows the sliders), pushed out to the mop's thickness, its edge hanging over the hairline (most on
  the forehead), closed underneath. UV.x runs 0 inside to 1 at the edge (where the shader cuts the fringe into
  curls); UV2 is metres.
- `moustache`: the skin between the nose and the upper lip, out past the corners of the mouth, pushed out. UV.x runs
  from the middle (0) to each end (1), UV.y across it; UV2 the same in metres.
The numbers at the top are Claude's picks.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402
import figed_fit  # noqa: E402
import garments as G  # noqa: E402

SIZE = 1024
# the hairline: degrees round the head from the front -> height over the eye line (shares of eye-to-crown where
# under 1 in size and marked "s", else metres)
LINE_A = [0, 35, 55, 72, 95, 125, 180]
LINE_S = [0.60, 0.56, 0.30, 0.0, 0.0, 0.0, 0.0]            # share of eye-to-crown
LINE_M = [0.0, 0.0, 0.0, -0.035, -0.015, -0.075, -0.085]   # plus metres
THICK = (0.012, 0.036)                                     # the mop's thickness at the hairline, and further in
FRINGE = 0.03                                              # how far in from its edge the shader may cut the mop
SAG_A = [0, 50, 80, 120, 180]                              # degrees round from the front -> how far the mop's edge
SAG_M = [0.06, 0.042, 0.026, 0.014, 0.02]                 # hangs down over the hairline there (metres)
HAIR = ((0.20, 0.105, 0.06), (0.34, 0.185, 0.10), (0.52, 0.30, 0.16))   # crease, strand, light (amber)
TACHE = ((0.40, 0.17, 0.07), (0.60, 0.29, 0.13), (0.74, 0.42, 0.20))    # ginger: redder than his hair


INFO = {}


def _biggest(mesh):
    """Only the largest joined piece of a mesh is kept (stray flecks cut off by a fold of skin go)."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    left, best = set(bm.verts), []
    while left:
        grp, todo = set(), [next(iter(left))]
        while todo:
            v = todo.pop()
            if v in grp:
                continue
            grp.add(v)
            todo.extend(e.other_vert(v) for e in v.link_edges)
        left -= grp
        if len(grp) > len(best):
            best = grp
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in best], context="VERTS")
    bm.to_mesh(mesh)
    bm.free()


def landmarks(fig, P):
    base = fig.base
    z = P[:, 2]
    headw = G._w(base, ("head",))
    eye = (P[base.indices("helper-l-eye")].mean(axis=0) + P[base.indices("helper-r-eye")].mean(axis=0)) / 2
    crown = float(z[headw > 0.8].max())
    idx, d = base.target("mouth-scale-horiz-incr")
    size = np.linalg.norm(d, axis=1)
    corner = P[int(idx[np.argmax(np.where(P[idx, 0] > 0, size, -1))])]
    idx, d = base.target("mouth-philtrum-volume-incr")
    mid = idx[np.abs(P[idx, 0]) < 0.006]
    L = {"eye": eye, "crown": crown, "corner": corner, "nose_base": float(P[mid, 2].max()),
         "lip_top": float(P[mid, 2].min())}
    print("landmarks: eye z %.3f crown %.3f mouth corner x %.3f z %.3f nose base %.3f lip top %.3f"
          % (eye[2], crown, corner[0], corner[2], L["nose_base"], L["lip_top"]))
    return L


def rules(fig, P, H):
    base = fig.base
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L = landmarks(fig, P)
    headw = G._w(base, ("head",))
    ears = np.zeros(len(P), dtype=bool)
    for _side, masks in fig._ear_masks().items():
        ears[np.asarray(masks[0], dtype=int)] = True
    eye = L["eye"]
    span = L["crown"] - eye[2]
    yc = H["head"][1]
    a = np.degrees(np.abs(np.arctan2(x, -(y - yc))))
    line = eye[2] + np.interp(a, LINE_A, LINE_S) * span + np.interp(a, LINE_A, LINE_M)
    f = z - line
    thick = THICK[0] + THICK[1] * np.clip(f / 0.04, 0, 1) ** 0.6
    out = {"hair": (f, (headw > 0.5) & ~ears, thick)}
    xe = abs(L["corner"][0]) + 0.02
    zc = L["corner"][2]
    t = np.clip(np.abs(x) / xe, 0, 1)
    top = L["nose_base"] - 0.002
    top = top - (top - (zc + 0.006)) * t ** 2.2
    bot = L["lip_top"] - 0.006
    bot = bot + ((zc - 0.009) - bot) * t ** 1.5
    fm = np.minimum(np.minimum(top - z, z - bot), (xe - np.abs(x)) * 0.5)
    out["moustache"] = (fm, (headw > 0.5) & (y < eye[1] + 0.03), 0.004 + 0.008 * np.clip(fm / 0.006, 0, 1))
    INFO.update(top=top, bot=bot, yc=yc)
    return out, L


def _uv_layers(bm):
    """(UV, UV2) of a bmesh: both made first, then looked up (making one moves the other)."""
    if bm.loops.layers.uv.get("UVMap") is None:
        bm.loops.layers.uv.new("UVMap")
    if bm.loops.layers.uv.get("UV2") is None:
        bm.loops.layers.uv.new("UV2")
    if bm.loops.layers.color.get("Col") is None:
        bm.loops.layers.color.new("Col")
    return bm.loops.layers.uv.get("UVMap"), bm.loops.layers.uv.get("UV2")


def shell(mesh, skin):
    """The cut scalp made the mop's smooth outer surface: divided once, its edge hung over the hairline, closed
    underneath, with the hair shader's coordinates."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=0.6)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts])
    lf = bm.verts.layers.float.get("f")
    _ = lf
    # how far each point is from the mop's edge, over the surface near enough (the rule's own value is a HEIGHT over
    # the hairline: across the flat top of the head it stays small a long way in)
    B = np.array([v.co[:] for v in bm.verts if v.is_boundary])
    fv = np.array([np.linalg.norm(B - q, axis=1).min() for q in V])
    c = V.mean(axis=0)
    ang = np.degrees(np.abs(np.arctan2(V[:, 0] - c[0], -(V[:, 1] - c[1]))))
    sag = np.interp(ang, SAG_A, SAG_M) * np.clip(1 - fv / 0.04, 0, 1) ** 1.5
    V2 = V.copy()
    V2[:, 2] -= sag
    # ... and stays outside the head as it hangs (the forehead comes forward under the hairline)
    for i in np.nonzero(sag > 0.002)[0]:
        q = skin[np.argmin(np.linalg.norm(skin - V2[i], axis=1))]
        r = q - c
        r[2] *= 0.3
        r /= np.linalg.norm(r)
        out = (V2[i] - q).dot(r)
        if out < 0.014:
            V2[i] += r * (0.014 - out)
    for v, q in zip(bm.verts, V2):
        v.co = q
    # (measured again now that the edge has hung down: the hanging band is stretched)
    B = np.array([v.co[:] for v in bm.verts if v.is_boundary])
    edge_d = {v: float(np.linalg.norm(B - np.array(v.co[:]), axis=1).min()) for v in bm.verts}
    # an under-layer: the same surface a little further in, never cut and drawn darker, so the gaps the shader cuts
    # between the curls at the edge show hair underneath, not his scalp
    inner = set()
    made = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])["geom"]
    for v in [g for g in made if isinstance(g, bmesh.types.BMVert)]:
        v.co = (c[0] + (v.co.x - c[0]) * 0.93, c[1] + (v.co.y - c[1]) * 0.93, c[2] + (v.co.z - c[2]) * 0.93)
        edge_d[v] = 0.2
        inner.add(v)
    rim = [e for e in bm.edges if e.is_boundary and e.verts[0] not in inner]
    made = bmesh.ops.extrude_edge_only(bm, edges=rim)["geom"]
    for v in [g for g in made if isinstance(g, bmesh.types.BMVert)]:
        q = np.array(v.co[:])
        v.co = skin[np.argmin(np.linalg.norm(skin - q, axis=1))]
        edge_d[v] = 0.2                                   # the underside is never cut into curls
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv, uv2 = _uv_layers(bm)
    col = bm.loops.layers.color.get("Col")
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            d = edge_d[loop.vert]
            shade = 0.5 if loop.vert in inner else 1.0
            loop[col] = (shade, shade, shade, 1.0)
            a = math.atan2(loop.vert.co.x - c[0], -(loop.vert.co.y - c[1]))
            loop[uv].uv = (1.0 - min(0.97, d / FRINGE), a / (2 * math.pi) + 0.5)   # (never 0: the shader inks roots)
            loop[uv2].uv = (d, a * 0.09)
    bm.to_mesh(mesh)
    bm.free()


def moustache_uv(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    V = np.array([v.co[:] for v in bm.verts])
    lo, hi = V.min(axis=0), V.max(axis=0)
    mid, half = (lo[0] + hi[0]) / 2, (hi[0] - lo[0]) / 2
    uv, uv2 = _uv_layers(bm)
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            ax = abs(loop.vert.co.x - mid)
            # (strands run out from the middle and droop to the ends: "across" is measured from that drooping line)
            w = loop.vert.co.z + (hi[2] - lo[2]) * 0.75 * (ax / half) ** 2
            loop[uv].uv = (ax / half, min(1.0, max(0.0, (w - lo[2]) / (hi[2] - lo[2]) * 0.8)))
            loop[uv2].uv = (ax, w - lo[2])
    bm.to_mesh(mesh)
    bm.free()


def make(fig, wear, stem):
    base = fig.base
    P, H, T = fig.to_blender()
    Pp = figed_fit.pose_points(fig, P, H, figed_fit.full_pose(fig.pose, base.bones, H, T), T)[0]
    R, L = rules(fig, P, H)
    G.SMOOTH.update(hair=2, moustache=1)
    skin = Pp[G._w(base, ("head",)) > 0.5]
    objs = {}
    for name in wear:
        f, may, off = R[name]
        mesh = G.cut(fig, P, Pp, f, may, off, name)
        for v, d in zip(mesh.vertices, mesh.attributes["posed"].data):
            v.co = d.vector
        _biggest(mesh)
        if name == "hair":
            shell(mesh, skin)
            mesh.color_attributes.render_color_index = mesh.color_attributes.find("Col")
            mesh.color_attributes.active_color = mesh.color_attributes["Col"]
        else:
            moustache_uv(mesh)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        mesh.materials.append(G.plain_material(name, HAIR[1] if name == "hair" else TACHE[1]))
        objs[name] = obj
        print("%-10s %5d triangles" % (name, sum(len(p.vertices) - 2 for p in mesh.polygons)))
    return objs


if __name__ == "__main__":
    import figed_blender as fb  # noqa: E402

    argv = sys.argv[sys.argv.index("--") + 1:]
    spec_path, out = argv[:2]
    wear = argv[argv.index("--wear") + 1].split(",") if "--wear" in argv else ["hair", "moustache"]
    fig = figed.Figure(figed.Base(), figed.load_spec(spec_path))
    stem = os.path.splitext(spec_path)[0]
    fb.reset()
    objs, _arm = fb.build(fig, rig=False, posed=True)
    objs["body"].data.materials.append(G.material("skin", stem + "_skin.png"))
    if "eyes" in objs and os.path.exists(stem + "_eyes.png"):
        objs["eyes"].data.materials.append(G.material("eyes", stem + "_eyes.png"))
    make(fig, wear, stem)
    if "--glb" in argv:                                   # the head with its hair, for Godot (tests/figed_hair_view.gd)
        bpy.ops.export_scene.gltf(filepath=os.path.abspath(argv[argv.index("--glb") + 1]), export_format="GLB",
                                  export_yup=True, export_animations=False)
    boxes = fb.view_boxes(fig)
    cam = fb._camera()
    strips = []
    for view in ("face", "face_quarter_r", "face_side_r", "face_quarter", "face_back"):
        centre, direction, seen, aspect = boxes[view][:4]
        seen = seen * 1.12                                # room for the hair
        w = int(900 * aspect) // 2 * 2
        s = fb._scene((w, 900))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT" if "--lit" not in argv else "STUDIO"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, direction, seen)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = seen
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(out)), "_hair_%s.png" % view)
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(900, w, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(out))
    print("shots", out)
