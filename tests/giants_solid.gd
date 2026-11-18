extends SceneTree
## Are the giants solid? (tools/QUALITY.md, CLAUDE.md "Decision: solid giants".) For each big kind
## in the sea, the player (a sardine, then a tuna) is put inside its body, beside its middle, and
## then steered straight at it for two seconds; how deep into the body it ever got is printed
## (0: it never got in past its skin and the player's own room). Also the reef-back, from Main's list.
##   godot --headless --path . --audio-driver Dummy --fixed-fps 60 -s res://tests/giants_solid.gd

const KINDS := ["humpback", "blue_whale", "leviathan", "submarine", "whale_shark", "sperm_whale", "ghost_whale", "manta", "orca"]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var scenery := Scenery.new()
	root.add_child(scenery)
	var player := Player.new()
	root.add_child(player)
	player.begin(Vector3(Sea.START.x, Sea.SURFACE - 5.0, Sea.START.y), "sardine")
	var life := Life.new()
	life.player = player
	life.hunting = false
	root.add_child(life)
	var walker: Variant = scenery.get(&"_reef_back")
	if walker is Node3D:
		life.solids.append([walker, Vector3(0.0, 8.5, 0.0), 12.0, 4.5])
	await process_frame
	var failed := 0
	for as_kind in ["sardine", "tuna"]:
		for kind: String in KINDS:
			var body: Creature = null
			for c: Creature in life.creatures:
				if c.kind == kind:
					body = c
					break
			if body == null:
				continue
			player.begin(body.global_position, as_kind)
			player.safe = 0.0
			body.dress()
			var deepest := 0.0
			for i in 120:
				# (the player steered straight at the body's middle all the while)
				var to := body.global_position - player.global_position
				if to.length() > 0.01:
					player.yaw = atan2(-to.x, -to.z)
					player.pitch = asin(clampf(to.normalized().y, -1.0, 1.0))
				player.throttle = 1.0
				player.step(1.0 / 60.0)
				life.step(1.0 / 60.0)
				var half := body.length * (0.5 - Life.BODY)
				var on := clampf((player.global_position - body.global_position).dot(body.heading), -half, half)
				var into := body.length * Life.BODY - player.global_position.distance_to(body.global_position + body.heading * on)
				if i > 2:
					deepest = maxf(deepest, into)
				await process_frame
			var ok := deepest <= 0.05
			failed += int(not ok)
			print("SOLID %s as a %s: deepest into its body %.2f m (%s)" % [kind, as_kind, deepest, "ok" if ok else "FAILED"])
	if walker is Node3D:
		var w: Node3D = walker
		player.begin(w.global_transform * Vector3(0.0, 8.5, 0.0), "tuna")
		player.safe = 0.0
		life.step(1.0 / 60.0)
		var middle: Vector3 = w.global_transform * Vector3(0.0, 8.5, 0.0)
		print("SOLID reef_back: put in its middle, now %.2f m from it (its trunk 4.5 m round)" % player.global_position.distance_to(middle))
	print("SOLID %s" % ("PASSED" if failed == 0 else "FAILED"))
	quit(0)
