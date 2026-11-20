extends SceneTree
## A dressed figed figure on its skeleton (tools/figed/garments.py ... --glb <file>) bent into test poses in Godot, to
## see that the body, clothes, boots and hard parts follow the bones before any animation is made for it. One strip a
## pose (front, three-quarter, side, back), stacked: rest, a walking stride, a reach and crouch, a swim stroke.
##   godot --path . --audio-driver Dummy --resolution 420x520 --position 2600,60 -s tests/figed_pose_view.gd -- \
##       --glb=<file.glb> --out=<sheet.png>
## Bones are turned about model axes from rest (x: his left, y: up, z: toward the camera in the front view).

const HAIR := preload("res://shaders/ink/hair_ink.gdshader")
const POSES := {
	"rest": [],
	"stride": [["thigh_l", Vector3.RIGHT, -32], ["calf_l", Vector3.RIGHT, 28], ["thigh_r", Vector3.RIGHT, 24],
			["calf_r", Vector3.RIGHT, 38], ["foot_r", Vector3.RIGHT, 20], ["upperarm_l", Vector3.FORWARD, 62],
			["upperarm_r", Vector3.FORWARD, -62], ["upperarm_l", Vector3.RIGHT, 26], ["upperarm_r", Vector3.RIGHT, -30],
			["lowerarm_r", Vector3.RIGHT, -40], ["lowerarm_l", Vector3.RIGHT, -18], ["spine_02", Vector3.UP, 8],
			["head", Vector3.UP, -10]],
	"reach": [["thigh_l", Vector3.RIGHT, -70], ["calf_l", Vector3.RIGHT, 85], ["thigh_r", Vector3.RIGHT, -55],
			["calf_r", Vector3.RIGHT, 80], ["spine_01", Vector3.RIGHT, 22], ["spine_03", Vector3.RIGHT, 14],
			["upperarm_l", Vector3.FORWARD, 20], ["upperarm_l", Vector3.RIGHT, -75], ["upperarm_r", Vector3.FORWARD, -60],
			["lowerarm_l", Vector3.RIGHT, -25], ["head", Vector3.RIGHT, -18]],
	"swim": [["upperarm_l", Vector3.FORWARD, -70], ["upperarm_r", Vector3.FORWARD, 70], ["thigh_l", Vector3.RIGHT, -18],
			["thigh_r", Vector3.RIGHT, 22], ["calf_r", Vector3.RIGHT, 30], ["spine_02", Vector3.RIGHT, -12],
			["head", Vector3.RIGHT, -20], ["foot_l", Vector3.RIGHT, 35], ["foot_r", Vector3.RIGHT, 35]],
}
const VIEWS := [0.0, -45.0, -90.0, 180.0]

var _glb := ""
var _out := ""
var _skel: Skeleton3D


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--glb="):
			_glb = a.substr(6)
		elif a.begins_with("--out="):
			_out = a.substr(6)
	_run.call_deferred()


func _find(n: Node, into: Array) -> void:
	if n is Skeleton3D:
		_skel = n
	if n is MeshInstance3D:
		into.append(n)
	for c in n.get_children():
		_find(c, into)


func _turn(bone: String, axis: Vector3, deg: float) -> void:
	var b := _skel.find_bone(bone)
	if b < 0:
		print("no bone ", bone)
		return
	var g := _skel.get_bone_global_rest(b).basis.orthonormalized()
	var d := g.inverse() * Basis(axis, deg_to_rad(deg)) * g
	_skel.set_bone_pose_rotation(b, _skel.get_bone_pose_rotation(b) * d.get_rotation_quaternion())


func _run() -> void:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(_glb, state) != OK:
		push_error("cannot read " + _glb)
		quit(1)
		return
	var model: Node3D = doc.generate_scene(state)
	root.add_child(model)
	var meshes: Array = []
	_find(model, meshes)
	var tris := 0
	for m in meshes:
		for s in m.mesh.get_surface_count():
			tris += m.mesh.surface_get_array_index_len(s) / 3
		var key := String(m.name).to_lower()
		if key.begins_with("hair") or key.begins_with("moustache"):
			var mat := ShaderMaterial.new()
			mat.shader = HAIR
			var dark := key.begins_with("hair")
			mat.set_shader_parameter("albedo", Color(0.215, 0.115, 0.062) if dark else Color(0.55, 0.25, 0.1))
			mat.set_shader_parameter("ink", Color(0.085, 0.04, 0.025) if dark else Color(0.25, 0.09, 0.04))
			var look := {"soft": 1.0, "metres": 1.0, "root_ink": 0.0, "lit_lines": 0.0, "shadow_lines": 0.0, "wrap": 1.0,
					"flatness": 1.0, "shadow_fill": 0.85, "lighten": 0.12, "print_grain": 0.0, "gap_ink": 0.1,
					"curl": 0.8 if dark else 0.0, "curl_size": 0.036, "curl_gaps": 0.45, "curl_rim": 0.9 if dark else 0.0,
					"curl_edge": 0.3 if dark else 0.0, "layer_shade": 1.0 if dark else 0.0}
			for k in look:
				mat.set_shader_parameter(k, look[k])
			m.material_override = mat
	print("figure: ", meshes.size(), " meshes, ", tris, " triangles, ", _skel.get_bone_count(), " bones")
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.9, 0.9, 0.92)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.8
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 2.1
	root.add_child(cam)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.6
	cam.add_child(sun)
	sun.rotation_degrees = Vector3(-30, 25, 0)
	var centre := Vector3(0, 0.92, 0)
	var size := root.size
	var sheet := Image.create(size.x * VIEWS.size(), size.y * POSES.size(), false, Image.FORMAT_RGBA8)
	var row := 0
	for pose in POSES:
		_skel.reset_bone_poses()
		for step in POSES[pose]:
			_turn(step[0], step[1], step[2])
		for i in VIEWS.size():
			var a := deg_to_rad(VIEWS[i])
			cam.position = centre + Vector3(sin(a), 0, cos(a)) * 5.0
			cam.look_at(centre)
			for _f in 4:
				await process_frame
			var shot := root.get_texture().get_image()
			shot.convert(Image.FORMAT_RGBA8)
			sheet.blit_rect(shot, Rect2i(Vector2i.ZERO, size), Vector2i(size.x * i, size.y * row))
		row += 1
	sheet.save_png(_out)
	print("saved ", _out)
	quit()
