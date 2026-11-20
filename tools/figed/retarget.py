"""Ready-made motion clips carried onto a figed figure's own skeleton and proportions, baked as clips of its own.

    blender -b --factory-startup --python tools/figed/retarget.py -- <spec.json> <clips.glb> <out.glb> [--only a,b]

The clips are Quaternius's Universal Animation Library (CC0; kept OUTSIDE the repo in
C:\\Projects\\reference\\quaternius-ual, the file `Unreal-Godot/UAL1_Standard.glb`: 43 clips on Unreal's mannequin
layout, the same bone names as MakeHuman's "game engine" rig the figures use). The user's call (2026-11-20): "Lets
start with ready made motion clips".

How a clip is carried over (the usual way: turns measured in the world, not copied bone to bone, because the two
skeletons rest differently: theirs in a T-pose, ours with the arms lower, and their bones' own axes differ):
- at every frame, each of their bones' turn from ITS rest, measured in the world, is given to our bone of the same
  name from OUR rest;
- our arm and leg bones are first lined up with theirs (the turn that lays our resting bone along their resting
  bone), so a T-pose there is a T-pose here whatever angle our arms rest at;
- the hips' travel is scaled by the height of our hips over theirs (a shorter-legged figure takes shorter steps);
- bones they have and we do not (finger tips, a root) are skipped; ours without a partner keep their rest.
The result is one .glb: our skeleton alone with every clip baked on it (no mesh), named as the library names them.
Godot plays them on any dressed export of the same figure (`garments.py --glb`): same skeleton, same bone names.
"""
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402
import figed_blender as fb  # noqa: E402

LINE_UP = ("clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot")   # bones laid along theirs first


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    spec_path, clips_path, out = argv[:3]
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    fig = figed.Figure(figed.Base(), figed.load_spec(spec_path))
    fb.reset()
    objs, tgt = fb.build(fig, name="figure")
    for o in objs.values():                               # the skeleton alone is exported
        bpy.data.objects.remove(o, do_unlink=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(clips_path))
    src = next(o for o in bpy.data.objects if o not in before and o.type == "ARMATURE")
    actions = [a for a in bpy.data.actions if only is None or any(a.name.startswith(n) for n in only)]
    sname = {b.name.lower(): b.name for b in src.data.bones}
    order = []                                            # our bones, parents first

    def walk(b):
        order.append(b)
        for c in b.children:
            walk(c)
    for b in tgt.data.bones:
        if b.parent is None:
            walk(b)
    S0 = {b.name: (src.matrix_world @ b.matrix_local).to_3x3() for b in src.data.bones}
    T0 = {b.name: b.matrix_local.to_3x3() for b in tgt.data.bones}
    # A bone's line is from its joint to its child's joint (a bone's own tail is wherever the rig's maker left it).
    # Hands, feet, fingers and toes take the lining-up of the limb they hang from.
    NEXT = {"clavicle": "upperarm", "upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
    line = {}
    for b in order:
        s = sname.get(b.name.lower())
        part, _, side = b.name.partition("_")
        child = NEXT.get(part, "") + "_" + side
        if s and part in NEXT and child in tgt.data.bones and sname.get(child):
            dt = (tgt.data.bones[child].head_local - b.head_local).normalized()
            ds = (src.matrix_world @ src.data.bones[sname[child]].head_local
                  - src.matrix_world @ src.data.bones[s].head_local).normalized()
            line[b.name] = dt.rotation_difference(ds).to_matrix()
        elif b.parent and b.parent.name in line and part not in ("spine", "neck", "head", "pelvis"):
            line[b.name] = line[b.parent.name]
    print("lined up:", ", ".join("%s %.0f" % (k, v.to_quaternion().angle * 57.3) for k, v in line.items() if k.endswith("_l") and k.split("_")[0] in NEXT))
    hips = next(b for b in order if b.name.lower() == "pelvis")
    hips_s = src.data.bones[sname["pelvis"]]
    scale = hips.head_local.z / max(1e-6, (src.matrix_world @ hips_s.head_local).z)
    print("retarget: %d of our %d bones have a partner; hips %.3f over theirs %.3f = step scale %.2f; %d clips" % (
        sum(1 for b in order if b.name.lower() in sname), len(order), hips.head_local.z,
        (src.matrix_world @ hips_s.head_local).z, scale, len(actions)))
    bpy.context.view_layer.objects.active = tgt
    for pb in tgt.pose.bones:
        pb.rotation_mode = "QUATERNION"
    tgt.animation_data_create()
    src.animation_data_create()
    scene = bpy.context.scene
    made = []
    for act in actions:
        name = act.name.replace("_Armature", "")
        src.animation_data.action = act
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        new = bpy.data.actions.new(name)
        tgt.animation_data.action = new
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            W = {}
            for b in order:
                s = sname.get(b.name.lower())
                parent = b.parent.name if b.parent else None
                Wp0 = T0[parent] if parent else Matrix.Identity(3)
                Wp = W[parent] if parent else Matrix.Identity(3)
                if s:
                    Ms = (src.matrix_world @ src.pose.bones[s].matrix).to_3x3()
                    turn = Ms @ S0[s].inverted()
                    W[b.name] = turn @ line.get(b.name, Matrix.Identity(3)) @ T0[b.name]
                else:
                    W[b.name] = Wp @ Wp0.inverted() @ T0[b.name]
                rest_local = Wp0.inverted() @ T0[b.name]
                pose_local = Wp.inverted() @ W[b.name]
                pb = tgt.pose.bones[b.name]
                pb.rotation_quaternion = (rest_local.inverted() @ pose_local).to_quaternion()
                pb.keyframe_insert("rotation_quaternion", frame=f - f0 + 1)
            ps = src.matrix_world @ src.pose.bones[sname["pelvis"]].matrix.to_translation()
            rs = src.matrix_world @ hips_s.head_local
            move = (ps - rs) * scale                      # the hips' travel from their rest, in the world, scaled
            hp = tgt.pose.bones[hips.name]
            Wp0 = T0[hips.parent.name] if hips.parent else Matrix.Identity(3)
            Wp = W[hips.parent.name] if hips.parent else Matrix.Identity(3)
            hp.location = T0[hips.name].inverted() @ (Wp0 @ Wp.inverted() @ Vector(move))
            hp.keyframe_insert("location", frame=f - f0 + 1)
        made.append((name, new, f1 - f0 + 1))
    tgt.animation_data.action = None
    for name, new, _n in made:                            # one track a clip: the exporter names clips by track
        track = tgt.animation_data.nla_tracks.new()
        track.name = name
        track.strips.new(name, 1, new)
    for o in list(bpy.data.objects):
        if o is not tgt:
            bpy.data.objects.remove(o, do_unlink=True)
    scene.render.fps = 30
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(out), export_format="GLB", export_yup=True,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True,
                              export_force_sampling=True, export_optimize_animation_size=False)
    print("clips:", ", ".join("%s(%d)" % (n, k) for n, _a, k in made))
    print("exported", out)


if __name__ == "__main__":
    main()
