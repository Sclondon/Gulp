class_name Arena
extends Node3D
## The other players, when the game is online: everyone playing shares one sea of players (the
## rest of the sea's life is each game's own). A player eats another whose fish is no longer
## than 0.8 of its own, by the game's one rule; the server (scareathon-v3 server/gulp/arena.js)
## settles who ate whom and keeps the high scores. If the server cannot be reached the game is
## simply played alone.
##
## Each rival is a Fish moved towards the last state its own game sent, with its name over it.

signal board_changed

const Net := preload("res://scripts/arena_net.gd")
const K_STATE := 1
const STATE_BYTES := 14
## States sent a second.
const RATE := 15.0

var player: Player
## Connected and let in.
var online := false
## Our own id in the room.
var me := 0
## The high scores: each [name, length, kind], longest first.
var top: Array = []
## The other players: id -> Rival.
var rivals := {}
## What has happened, for the tests: "ate <id>", "eaten by <id>".
var log_lines: Array[String] = []

var _net: Node
var _send_in := 0.0
var _grow_in := 0.0
var _told_kind := ""
var _told_length := 0.0
var _claimed := {}
var _dead_told := false


## Joins the shared sea on a server, under a name.
func open(server: String, player_name: String) -> void:
	_net = Net.new()
	add_child(_net)
	_net.message.connect(_on_message)
	_net.states.connect(_on_states)
	_net.failed.connect(_on_failed)
	_net.open(player_name, server)


## How many fish hunting the player just now are other players.
func hunters() -> int:
	var found := 0
	for rival: Rival in rivals.values():
		if rival.alive and Life.can_eat(rival.length, player.length) and rival.global_position.distance_to(player.global_position) < 4.0 + rival.length * 3.0:
			found += 1
	return found


func step(delta: float) -> void:
	for rival: Rival in rivals.values():
		rival.follow(delta)
	if not online:
		return
	# Our own fish's state, a few times a second.
	_send_in -= delta
	if _send_in <= 0.0 and player.alive:
		_send_in = 1.0 / RATE
		_net.send_states(_state())
	# What it is and how long, when that has changed.
	_grow_in -= delta
	if player.alive and _grow_in <= 0.0 and (player.kind != _told_kind or absf(player.length - _told_length) > 0.005):
		_grow_in = 0.4
		_told_kind = player.kind
		_told_length = player.length
		_net.send({"t": "grow", "kind": player.kind, "len": snappedf(player.length, 0.001)})
	if not player.alive:
		return
	# Its mouth on a smaller player: a claim, which the server grants or not.
	var mouth := player.mouth()
	for id: int in rivals:
		var rival: Rival = rivals[id]
		if not rival.alive or player.safe > 0.0 or player.in_air:
			continue
		if Life.can_eat(player.length, rival.length) and rival.global_position.distance_to(mouth) < player.length * 0.3 + rival.length * 0.35:
			var last: float = _claimed.get(id, -1.0)
			var now := Time.get_ticks_msec() / 1000.0
			if now - last > 0.3:
				_claimed[id] = now
				_net.send({"t": "ate", "v": id})


## The player was eaten by something in its own sea.
func died(by: String) -> void:
	if online and not _dead_told:
		_dead_told = true
		_net.send({"t": "died", "by": by})


## A new run.
func spawn() -> void:
	_told_kind = ""
	_dead_told = false
	if online:
		_net.send({"t": "spawn"})


func _state() -> PackedByteArray:
	var out := StreamPeerBuffer.new()
	out.put_u8(K_STATE)
	out.put_u8(me)
	out.put_u8((1 if player.in_air else 0) | (2 if player.boosting else 0))
	var at := player.global_position
	out.put_16(clampi(roundi(at.x * 100.0), -32767, 32767))
	out.put_16(clampi(roundi(at.y * 100.0), -32767, 32767))
	out.put_16(clampi(roundi(at.z * 100.0), -32767, 32767))
	var way := player.heading
	out.put_16(roundi(wrapf(atan2(-way.x, -way.z), -PI, PI) * 10000.0))
	out.put_16(roundi(asin(clampf(way.y, -1.0, 1.0)) * 10000.0))
	out.put_u16(clampi(roundi(player.length * 1000.0), 0, 65535))
	return out.data_array


func _on_states(data: PackedByteArray) -> void:
	if data.size() != 1 + STATE_BYTES:
		return
	var from := StreamPeerBuffer.new()
	from.data_array = data
	from.seek(1)
	var id := from.get_u8()
	var flags := from.get_u8()
	var rival: Rival = rivals.get(id)
	if rival == null:
		return
	var at := Vector3(from.get_16(), from.get_16(), from.get_16()) / 100.0
	var yaw := from.get_16() / 10000.0
	var pitch := from.get_16() / 10000.0
	rival.length = from.get_u16() / 1000.0
	rival.hear(at, yaw, pitch, flags & 2 != 0)


func _on_message(m: Dictionary) -> void:
	match m.get("t", ""):
		"welcome":
			online = true
			me = int(m.you)
			for each: Dictionary in m.ents:
				_add(each)
			_set_top(m.get("top", []))
		"ent":
			_add(m)
		"gone":
			var gone: Rival = rivals.get(int(m.id))
			if gone:
				rivals.erase(int(m.id))
				gone.queue_free()
		"grow", "alive":
			var rival: Rival = rivals.get(int(m.e))
			if rival:
				rival.length = float(m.len)
				if rival.kind != String(m.kind):
					rival.set_kind(String(m.kind))
				if m.t == "alive":
					rival.alive = true
					rival.fresh = true
		"kill":
			var victim := int(m.v)
			if victim == me:
				if int(m.a) != 0:
					log_lines.append("eaten by %d" % int(m.a))
					_dead_told = true
					player.safe = 0.0
					player.die("player")
			else:
				var eaten: Rival = rivals.get(victim)
				if eaten:
					eaten.alive = false
					eaten.visible = false
				if int(m.a) == me:
					log_lines.append("ate %d" % victim)
					player.feed(float(m.len))
		"top":
			_set_top(m.get("top", []))


func _set_top(to: Array) -> void:
	top = to
	board_changed.emit()


func _add(each: Dictionary) -> void:
	var id := int(each.id)
	if id == me or rivals.has(id):
		return
	var rival := Rival.new()
	add_child(rival)
	rival.length = float(each.len)
	rival.set_kind(String(each.kind))
	rival.called = String(each.name)
	rival.alive = bool(each.alive)
	rival.visible = false
	rivals[id] = rival


func _on_failed() -> void:
	online = false
	for rival: Rival in rivals.values():
		rival.queue_free()
	rivals.clear()


## Another player's fish.
class Rival:
	extends Fish

	var alive := true
	## Not yet heard from since it (re)appeared: its next state puts it straight there.
	var fresh := true
	var called := "": set = _set_called

	var _at := Vector3.ZERO
	var _way := Vector3.FORWARD
	var _boost := false
	var _label: Label3D

	func _set_called(to: String) -> void:
		called = to
		if _label == null:
			_label = Label3D.new()
			_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
			_label.no_depth_test = true
			_label.fixed_size = true
			_label.pixel_size = 0.0012
			_label.modulate = Color(0.85, 0.95, 1.0, 0.9)
			add_child(_label)
		_label.text = to

	## A state from its own game.
	func hear(at: Vector3, yaw: float, pitch: float, boosting: bool) -> void:
		_at = at
		_way = Vector3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
		_boost = boosting
		if fresh:
			fresh = false
			global_position = at
			heading = _way
		visible = alive

	func follow(delta: float) -> void:
		if not visible:
			return
		var before := heading
		velocity = (_at - global_position) * 8.0
		global_position = global_position.lerp(_at, 1.0 - exp(-10.0 * delta))
		heading = heading.slerp(_way, 1.0 - exp(-10.0 * delta)).normalized() if heading.angle_to(_way) > 0.001 else _way
		pose(delta, 2.0 if _boost else 1.0, clampf(-before.cross(heading).y / maxf(delta, 0.001) * 0.5, -1.0, 1.0))
		if _label:
			_label.position = Vector3(0.0, length * 0.5 + 0.15, 0.0)
			# (pose turns this node: the label stays upright because it is a billboard)
