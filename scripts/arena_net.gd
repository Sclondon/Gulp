extends Node
## The connection to the shared sea on the Scareathon server (/gulp/ws; see server/gulp/arena.js
## in scareathon-v3). Everyone who plays online drops into the same room. The server keeps what
## all the games have to agree on (who is in, what each fish is and how long, who ate whom, the
## high scores); each game moves its own fish and keeps its own sea life.
##
## Text messages are JSON, both ways:
##   to the server:  join {name}  ·  grow {kind, len}  ·  ate {v} (my fish ate player v)  ·
##     died {by} (something in my own sea ate me)  ·  spawn
##   from it:  welcome {you, ents, top}  ·  ent {...} / gone {id}  ·  grow {e, kind, len}  ·
##     kill {a, v, len, kind}  ·  alive {e, kind, len}  ·  top {top}
## Binary packets are fish states (Arena packs them: 14 bytes after a kind byte), passed on by the
## server to everyone else as they are. After Liquid Metal.s scripts/arena_net.gd.

signal message(m: Dictionary)
signal states(data: PackedByteArray)
signal failed # couldn't get in, or the connection dropped

const PATH := "/gulp/ws"
const K_STATE := 1
const GIVE_UP := 6.0 # seconds to wait to be let in

var online := true
var _ws: WebSocketPeer
var _name := ""
var _waiting := 0.0
var _welcomed := false
var _joined := false


func open(player_name: String, server: String) -> void:
	_name = player_name
	_ws = WebSocketPeer.new()
	_ws.inbound_buffer_size = 1 << 18
	var url := server.trim_suffix("/").replace("https://", "wss://").replace("http://", "ws://") + PATH
	if _ws.connect_to_url(url) != OK:
		_fail.call_deferred()


func close() -> void:
	if _ws:
		_ws.close()
	_ws = null


func send(m: Dictionary) -> void:
	if _ws and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		_ws.send_text(JSON.stringify(m))


func send_states(data: PackedByteArray) -> void:
	if _ws and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN and _welcomed:
		_ws.send(data, WebSocketPeer.WRITE_MODE_BINARY)


func _fail() -> void:
	if _ws == null:
		return
	close()
	failed.emit()


func _process(delta: float) -> void:
	if _ws == null:
		return
	_ws.poll()
	match _ws.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			if not _joined:
				_joined = true
				send({ t = "join", name = _name })
			while _ws and _ws.get_available_packet_count() > 0:
				var data := _ws.get_packet()
				if not _ws.was_string_packet():
					if data.size() > 1 and data[0] == K_STATE:
						states.emit(data)
					continue
				var m: Variant = JSON.parse_string(data.get_string_from_utf8())
				if m is Dictionary:
					if m.get("t") == "welcome":
						_welcomed = true
					elif m.get("t") == "full":
						_fail()
						return
					message.emit(m)
		WebSocketPeer.STATE_CLOSED:
			_fail()
			return
	if not _welcomed:
		_waiting += delta
		if _waiting > GIVE_UP:
			_fail()
