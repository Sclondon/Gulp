# Brief: a "game" model for each sea creature, at Twilight Princess weight

The creature components in `C:\Projects\GameCommon\godot\<name>` (built 2026-11-17 for the game Gulp) each have a
full model and a low model. The user looked at their wireframes and triangle counts on 2026-11-18 and said: "We should
have a twilight princess model to compare to so we can make low poly versions while maintaining high quality looks and
silhouettes", and then: "just rebuild all of them, and keep the high quality version as well".

So: **add a third model to each component you are given, the game model**, built by the same Blender build script,
and keep the full and low models exactly as they are.

## The yardstick (the user's own reference models, measured on this machine)

A whole Twilight Princess hero is 4,174 triangles (Link, Sumo) to 5,671 (Link, Zora armor). Wireframes of the second,
to LOOK at for how the triangles are spent (look only: copy nothing from it):
`C:\Users\stewa\AppData\Local\Temp\claude\be065d617517d416\9790e32c-36f1-4aaf-8ece-7f095c2906fe\scratchpad\tp_out2\tp_link_zora_front.png`
and `tp_link_zora_side.png` there. What it shows: triangles packed into the face, the hands and the edges of the
outline (boots, helmet, the long fin crest), and a few big triangles across flat stretches (chest, thighs).

Our models now: the full ones are 5,000 to 73,000 triangles spent as an even fine grid; the low ones (450 to 6,400)
are an even coarse grid, which starves the eye, the mouth and the fin edges as much as the flanks.

## What the game model is

- **Budget, by the animal's LENGTH** (triangles, all of it, both sides):

  | LENGTH | triangles |
  | --- | --- |
  | 4 m and more | 4,000 to 5,500 |
  | 1.5 to 4 m | 3,000 to 4,500 |
  | 0.5 to 1.5 m | 1,800 to 3,000 |
  | 0.15 to 0.5 m | 900 to 1,800 |
  | under 0.15 m | 400 to 900 |

- **Spent unevenly, as the reference spends them**: many round the outline as seen from the side, from above and from
  the front (the back's and belly's curves, the snout, the tail's and fins' edges and tips, a bill, a sail's scallops),
  on the eye (a round eye, not a five-sided star), the lips and the jaw's hinge so the mouth still opens cleanly, the
  gill cover's edge where it is a step in the model; few across smooth flanks, the inside of the mouth, the underside
  of thin fins. Fins that are thin blades can be single two-sided sheets if the shader culls back faces: then keep
  them closed blades but with almost no thickness detail. Teeth: fewer and simpler, but still there if the full model
  has them.
- **It must look like the full model**: the same proportions and fin layout, the same silhouette. It is not a
  decimation of the full mesh: build it from the build script's own curves and profiles with fewer, better placed
  rings and points (a decimate modifier may help on a part, if every part code, UV, UV2 and vertex colour the shader
  reads comes through exactly and the result is checked as below).
- **The same shader, unchanged in behaviour**: every UV, UV2, vertex colour and part number the shader and the node
  script read must be there with the same meaning, so the markings, the swimming, `curl`, `gape` (the jaw really
  opening, a dark mouth inside) and every other setting work on the game model as on the full one. Markings are drawn
  by the shader, so they stay sharp.
- **No automatic LODs**: Godot's importer makes thinned LOD meshes, and a model bent in the vertex shader then bends in
  straight pieces far off. Load the game mesh without them (see `without_lods(mesh)` in
  `C:\Projects\GameCommon\godot\garden-eels\files\creatures\garden_eel\garden_eel.gd`), or set `lod_bias` high.

## In the component

- `models/<snake>_game.glb` (for a component with several models: one per type, kind or stage, named the same way
  with `_game`), built by `tools/build_<snake>.py` in the same run as the others; the `.blend` keeps all three.
- On the node: a property **`game := false`** (the default keeps every project that uses the component looking as it
  does now). With `game` true the game model is shown in place of the full one; `low` still shows the low model.
- **With `game` true the full model must never be loaded** (load each model only when it is first shown), so that a
  game's web export can leave the full `.glb` files out. Say so in the README.
- A static `game_mesh()` (with the type/kind/stage argument where `mesh_of` has one) for a game that draws meshes
  itself.
- Add the new file(s) to `FILES.txt`. Update the README: the game model, its triangle count beside the others', the
  user's words above, what was Claude's pick, what was checked. Update the check script to cover the game model.

## Checks (all of them, for every model)

- The build script's `WINDING` line is ok for every part of the game model, and the check script reads every triangle
  of the imported game model back in Godot: none wound against its normals, none of the body's skin facing inward.
- **Silhouette**: render the full and the game model as flat black shapes from the side, from above and from the
  front at the same framing, and measure how much of the picture differs (pixels in one and not the other, as a share
  of the full model's pixels). Aim for under 2% from the side and above. Print it, and look at the two side by side.
- Pictures in Godot (GL Compatibility, a scratch project of your own), which you LOOK at: the game model beside the
  full one, shaded with its markings, from both sides, above, front and three-quarter; close on the head with the
  mouth shut and wide open; through a beat of its swimming; curled; and its wireframe beside the reference picture's
  density (in Godot: `RenderingServer.set_debug_generate_wireframes(true)` before anything loads, then
  `viewport.debug_draw = Viewport.DEBUG_DRAW_WIREFRAME`). If it reads as a different or cruder animal, fix it.
- The component's `example.gd` still runs headless with no errors, with `game` false and true.
- The full and low `.glb` files must come out unchanged in what they hold (same triangle counts and look): you are
  adding, not rebuilding the look. If the build script cannot rebuild them identically, leave the existing full and
  low files as they are and export only the game model.

## The workspace's rules

- You own ONLY the component folders named in your task. Other agents are working in sibling folders. Do not touch any
  game, GameCommon's top README, or any other component.
- Before changing a component, copy it whole into a new folder under your scratch folder (`before/<name>`).
- Blender: `"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" --background --python <script>`.
  Godot 4.7: `"C:\Program Files (x86)\Steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe"`.
  Neither is on PATH. No system Python.
- Every Godot run: `--audio-driver Dummy`, `</dev/null`, under `timeout`. Prefer `--headless`; a window only for
  pictures, short, off to one side (`--position 2600,60`); make sure it has ended (other sessions have Godot open:
  never close a process that is not yours). One Blender or Godot at a time. `--headless --import` before a first run.
- Scratch work only under
  `C:\Users\stewa\AppData\Local\Temp\claude\be065d617517d416\9790e32c-36f1-4aaf-8ece-7f095c2906fe\scratchpad\game-<your group name>`
  (never the scratchpad's root, never `/tmp`). Install into a scratch Godot project with
  `sh /c/Projects/GameCommon/kit.sh install godot/<name> <project> --force`. Never test in a game.
- No `rm`. Write files with the Write tool, not shell heredocs.
- Also load the `blender-models` skill and read `~/.claude/skills/godot-checks/GOTCHAS.md`.

## Your report

Brief. For each component: triangles full / game / low; the silhouette differences measured; how `game` is switched
and what `game_mesh` takes; what you looked at; anything not verified; limits (what the game model lost).

## Groups (2026-11-18)

Started: pelagic-small (sardine, anchovy, pacific-mackerel, wahoo, barracuda); tunas; billfish (sailfish, swordfish,
blue-marlin, mahi-mahi); basses; reef-four; sharks; flat (halibut and five rays); baleen; toothed; pinnipeds; discs
(butterflyfish, angelfish); reef-three (lionfish, parrotfish, wrasse); tangs (surgeonfish, blue-tang, clownfish);
crustaceans; cephalopods; river-a; river-b; river-c (carp, lamprey, moray-eel); deep; first-fish (sockeye-salmon,
cutthroat-trout, flying-fish, clown-loach, channel-catfish).

Not started yet (no free slot): aquarium-a (neon-tetra, guppy, betta); aquarium-b (goldfish, zebra-danio, corydoras,
platy); odd (nudibranch, the single garden eel, ammonite). Not planned: the jellies (moon jelly, sea nettle) and the
scenery, which are light already.

## Added 2026-11-18: cartoon eyes

The user, after the groups had started: "the eyes for most of them should be more cartoony and personalized".

- A shader setting **`cartoon_eyes`** (0: the eye as it is now, the default, so nothing else changes; 1: the cartoon
  eye) and a node property of the same name. It works on all three models. Gulp sets it to 1.
- The cartoon eye: bigger than life (the eye's dome may be scaled up in the vertex shader about its own middle, by a
  factor chosen for the animal, about 1.3 to 2), a clean white or pale sclera, a coloured iris, a big dark pupil and a
  bright highlight that stays put towards the light, with a dark outline so it reads from far off. Drawn in the shader
  on the eye's own surface (the game model's eye needs enough triangles to stay round: say 24 to 40 a side).
- **Personalized**: each animal gets its own eye, to suit what it is, not one eye stamped on all of them: iris colour,
  pupil shape (round, a cat's slit, a W, a bar, a keyhole), how much white shows, and a lid or brow line that gives it
  a character (a white shark's heavy menacing brow, a sardine's wide startled stare, a grouper's sleepy half lid, a
  clownfish's bright eager eye, a moray's small mean one, an otter's or seal's big soft dark eye). Say in the README
  what character you gave it.
- Two more settings so a game can bring it to life: **`eye_look`** (a Vector2, -1..1: the pupil and iris slide that
  way, right and up, in the eye's own plane) and **`blink`** (0 open to 1 shut: a lid the colour of the skin closes
  over it; for fish, which have no lids, it may be a quick squash of the eye instead).
- Animals with no proper eyes to speak of (krill specks in a school mesh, plankton) are left alone; the school meshes
  are left alone.
- Check it in pictures: `cartoon_eyes` 0 and 1 close on the head from the side, front and three-quarter, looking each
  way, and blinking; and that with 0 the animal looks exactly as before.
