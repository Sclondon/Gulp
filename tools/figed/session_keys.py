"""Two keys for a figed sculpt or paint window (the user has no numpad and should not need Blender's menus):

    F5  the texture on / off (off = plain grey with studio light, to judge the forms)
    F6  Sculpt Mode <-> Texture Paint (Sculpt Mode starts on the Grab brush, mirrored)

Run inside Blender: exec(open(".../session_keys.py").read()). sculpt_session.py runs it for every window.
"""
import bpy


def _view():
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            return area, next(r for r in area.regions if r.type == "WINDOW")
    return None, None


class FIGED_OT_texture(bpy.types.Operator):
    bl_idname = "figed.texture"
    bl_label = "figed: texture on / off"

    def execute(self, context):
        area, _region = _view()
        sh = area.spaces[0].shading
        sh.type = "SOLID"
        if sh.color_type == "TEXTURE":
            sh.color_type, sh.light = "MATERIAL", "STUDIO"
        else:
            sh.color_type, sh.light = "TEXTURE", "FLAT"
        return {"FINISHED"}


class FIGED_OT_mode(bpy.types.Operator):
    bl_idname = "figed.mode"
    bl_label = "figed: sculpt / paint"

    def execute(self, context):
        if context.mode == "SCULPT":
            if "figed_skin" in bpy.data.images:
                bpy.ops.object.mode_set(mode="TEXTURE_PAINT")
            return {"FINISHED"}
        bpy.ops.object.mode_set(mode="SCULPT")
        context.scene.tool_settings.sculpt.use_symmetry_x = True
        area, region = _view()
        try:
            with context.temp_override(area=area, region=region):
                bpy.ops.brush.asset_activate(
                    asset_library_type="ESSENTIALS",
                    relative_asset_identifier="brushes/essentials_brushes-mesh_sculpt.blend/Brush/Grab")
            context.scene.tool_settings.unified_paint_settings.size = 110
        except Exception as e:
            print("grab brush:", e)
        return {"FINISHED"}


for cls in (FIGED_OT_texture, FIGED_OT_mode):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass
kc = bpy.context.window_manager.keyconfigs.addon
if kc:
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    have = {k.idname for k in km.keymap_items}
    if "figed.texture" not in have:
        km.keymap_items.new("figed.texture", "F5", "PRESS")
    if "figed.mode" not in have:
        km.keymap_items.new("figed.mode", "F6", "PRESS")
print("figed keys: F5 texture, F6 sculpt/paint")
