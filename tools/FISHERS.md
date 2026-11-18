# Fishers: hooks, nets and trawlers

The user's words (2026-11-18), all they said about it: **"We need to add fisherman- hooks nets and trawlers"**.

Everything below is a reading of that sentence: the main session's (its brief to the agent that built it) and the
building agent's picks. None of it is the user's rule; change any of it freely. Nobody has played it by hand yet.

## What it is

People fishing from the surface are a danger in the sea, in three forms. All of it is `scripts/fishers.gd`
(`Fishers`, one node Main makes beside Life and steps after it, so it stands still while the player chooses what to
become). The gear is modelled in Blender: `tools/build_fishing_gear.py` writes `tools/blend/fishing_gear.blend` and
`models/fishing_gear.glb`. The trawlers are the title's shrimp boat (`models/shrimp_boat.glb`), loaded by path and
used as it is. Nets are drawn by `shaders/net.gdshader`.

### Hooks

- Ten lines: six hang from red and white floats (river, two in the sea grass, two on the sand flats, one in the open
  sea), four from the rods of two anglers' skiffs (over the kelp and over the reef: bottom fishing, the hook 1.3 m over
  the floor). Each line: a float (or rod tip), the line, a sinker 0.4 m above the hook, a hook with its bait.
- Two kinds of rig (`Fishers.RIGS`): a worm (counts as 0.07 m for the eating rule, the hook holds fish up to 0.9 m),
  and a small bait fish (0.2 m, holds up to 2.0 m) on the open-sea float and one rod of each skiff. Drawn 2 and 3 times
  life size so that they can be seen.
- The bait is food by the usual rule (`Life.is_food`). A fish whose mouth reaches it:
  - too long for the hook: takes the bait (a meal) and the line parts;
  - otherwise: **hooked**. The line hauls it up to the surface (it takes `HAUL_TIME` 7 s from where it bit, at least
    0.4 m/s; while it bursts the haul goes at 0.3 of that). At the surface it is lifted out with a splash and the run
    ends ("hook").
- A lost or taken bait comes back on its line 18 to 30 s later.
- Fish of the sea take baits too: a fish of the right size wandering within 6 m of a bait is now and then sent to it,
  and one whose mouth reaches it is hauled up and comes back later somewhere else, as anything eaten does.

### Nets

- Three (`Fishers.NETS`): two drift nets in the open sea, 5 m deep, hung from a row of orange floats at the surface;
  one bottom net across the gap between the kelp and the reef, 3.5 m tall, standing off the floor on its weights.
  Each has a marker buoy with a pole and flag over each end (the bottom net's with a rope down to it). A net is one
  curtain (`NetPanel`, a unit square scaled) under the net shader: thin pale strands in diamonds, see-through between
  them; beyond 6 m it fades towards a faint even sheet (20% at 26 m), so it is seen in time but does not shimmer.
- A fish that swims into one:
  - shorter than its smallest (0.3 m, the bottom net 0.25 m): through the mesh;
  - longer than its biggest (1.6 m, the bottom net 1.2 m): tears through, leaving a ragged hole;
  - in between: **caught in the mesh**. It is held where it went in; after `NET_HOLD` 10 s the net is hauled and the
    run ends ("net"). Hunters can still come for it meanwhile.
- Holes are mended after 60 s (six at most to a net). Sea life of the right size that swims into a net hangs there
  for 25 to 40 s and is then gone (comes back later elsewhere); four at most to a net.

### Trawlers

- Two shrimp boats going round racetrack loops at 1.3 m/s (`Fishers.LOOPS`): one over the open sea (x 90 to 150),
  one along the shelf's edge (x 48 to 72). Each tows a trawl 32 m behind it along its way: two warps from its stern
  to a pair of otter doors 11 m apart, bridles from the doors to the trawl's mouth, and the trawl itself (`Trawl`: a
  funnel of net, its mouth 6 m wide and 3 m high with a headrope of floats and a heavy footrope, tapering to a cod end
  8 m back and a bag to 9.8 m). The open-sea trawl's mouth is 8 m down, the other's 13 m, never nearer the floor than
  2.2 m. From below, each boat is a dark hull with a wake of bubbles streaming from its stern.
- A fish (no longer than 2.6 m: a longer one tears through) that comes in through the mouth, swum in or swept in as
  the trawl comes over it, is held inside the funnel and goes back with the water to the cod end. Still in the cod end
  (7 m or more behind the mouth) after `CODEND_TIME` 5 s in all, it is caught and the run ends ("trawl").
- Ways out: swim out of the mouth faster than the tow (any fish at full ahead out-swims 1.3 m/s; the burst does it
  quickly), or, if small, through the mesh: under 0.3 m at the mouth down to under 0.1 m at the cod end.
- The giants (whales, the whale shark) are never caught. Up to six fish of the sea at a time are swept in, carried
  back to the cod end and hauled 4 s later.

### Getting free (hook and net)

- The struggle (`Fishers._struggle`): `grip` starts at 1. Holding the burst takes 0.42 a second off it, and 0.18 more
  while the fish points away from what holds it (down and away from the line; on through the net). Wriggling (the
  stick hard over) takes 0.1 a second, burst or not. At 0 it is free: the line parts, or it tears through the net to the
  far side. With a full burst (2.2 s of stamina) it is free in about 1.7 s; with none left, wriggling alone takes 10 s,
  which beats a net (10 s) only just and a hook only if it bit deep.
- After getting free, nothing catches it for 2 s (1 s after leaving a trawl).
- The Meter (`Fishers.Meter`, drawn over the controls): a brass-framed plate a third of the way down the screen with
  a symbol of what holds the fish (hook, net, trawl), an orange bar that runs down as it struggles (in a trawl: how
  far in it is, empty once out), a red bar of how near it is to being hauled, a flashing bolt (the burst), and a ring
  flashing round the burst button itself. No words.

### Fair to a new player

- Nothing is placed within 30 m of where every run starts (`START`, `SPARE`; the nearest hooks are further than that,
  the nets and trawl loops 40 m and more).
- A new run's sardine (0.18 m) swims through every net and is too small for the bait-fish hooks; the worm hooks are
  its danger. A fish that is hooked or netted always gets the same fair chance (full grip, seconds to spare).

## Numbers, all in `scripts/fishers.gd`

`RIGS`, `FLOATS`, `SKIFFS`, `SINKER_UP`, `HAUL_TIME`, `HAUL_SLOWEST`, `HAUL_FIGHT`, `REBAIT`, `STRUGGLE_*`, `SHAKEN`,
`NETS`, `NET_HOLD`, `NET_SPACING`, `NET_CATCH`, `LOOPS`, `TOW`, `LAG`, `STERN`, `DOORS`, `CODEND`, `CODEND_TIME`,
`TRAWL_BIG`, `TRAWL_PASS`, `TRAWL_CATCH`, `BOAT_SEEN` (75 m), `GEAR_SEEN` (70 m). The net's look: the uniforms of
`shaders/net.gdshader` (`mesh` 0.16 m, `strand`, `fade_near`, `fade_far`, `far_alpha`, `sway`).

## Arguments (read by Fishers itself)

```
godot --path . -- --near=hook            # start beside a float's bait (also skiff, net, trawl), nothing hunting
godot --path . -- --near=hook --catch    # ... and the gear still catches (to be hooked on purpose)
godot --path . -- --near=net --look=side # the eye put beside it (side, below, close; for the trawl also hull)
godot --path . -- --no-fishers           # none of it (to compare what a frame costs)
```

A timed run (`--seconds=`) prints `GULP FISHERS a frame ... ms` and a tally (hooked, freed, caught, snapped, netted,
tore, trawled, out of a trawl, sea life hooked/netted/trawled).

## Where it touches other files

- `scripts/main.gd`: `var fishers`, made after Effects (its meter added over the sea), `fishers.step` after
  `life.step`, `fishers.restart()` in `restart`, `bot.fishers`, and `hook`/`skiff`/`net`/`trawl` in `_go_near`.
- `scripts/player.gd`: `caught` (set by Fishers): while it is on, `step` turns and poses the fish but does not move it.
- `scripts/bot.gd`: keeps clear of `fishers.threats()`, and when held bursts the way of `fishers.way_out()` and
  wriggles. (Also: its long-declared "give up after a while with nothing eaten" was never wired up, and the bot sat
  against the floor; it now turns to krill after 6 s without a meal.)
- `tests/checks.gd` (`_fishing`), `tests/winding.gd` (every gear mesh).
- Run ends say "hook", "net" or "trawl" (`player.die`), so Main's `_on_died` and the bot's prints carry them.

## Checked (2026-11-18)

- `sh tests/smoke.sh`: twelve fishing checks pass: a bait hooks it; struggling frees it from the hook; left on the line
  it is hauled out; a fish too big for the hook snaps the line; one too small for the bait leaves it; a net holds a
  fish of its size; struggling frees it, through a hole; a fish too small swims through; one too big tears through; a
  trawl catches a fish that stays in it; a fish swims out of a trawl's mouth; one too big goes through a trawl.
- `sh tests/touch.sh`, `sh tests/bot.sh` pass. Bots started beside each kind (`--bot --catch --near=...`, 60 s each)
  kept clear of them all.
- Inside-out: in Blender every closed part of every piece (ray parity, `INSIDE-OUT PASSED`), and in Godot from the
  .glb (`tests/winding.gd`: winding agrees with normals on every triangle, solids enclose positive volume).
- Pictures (1280x720 and 390x844) of each from the side, below and close, the boat's hull from below, a fish on the
  hook and in a net with the meter. The gear rendered from five sides in Blender (`-- <folder>`).
- Cost: Fishers' own step about 0.2 ms a frame. Drawing: no difference beyond the noise between runs in back-to-back
  60 s bot runs with and without (`--no-fishers`).

## Not verified

- Nobody has played it: whether hooks are too easy to shake off (1.7 s of burst), whether the line reads as a warning
  in time, whether nets and trawls are too rare or too common.
- Never run on a phone, never in a web build (2,758 triangles of gear; each boat is 17,000, drawn within 75 m).
- The bot never met the gear by itself in its 240 s test (all of it is 30 m and more from the start).
- The shrimp boat's outriggers stay raised with their nets hanging to dry, as built (lowering them would leave their
  lines wrong: tools/SHRIMP_BOAT.md); the warps leave from the stern instead.
- The camera can pass through a net or into a trawl; nothing but the player and the fish of the sea feel them (the
  flocks of krill and sardines do not).
- No sound (an engine for the boats would be the first).
