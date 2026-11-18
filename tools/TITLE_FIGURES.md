# The title figures

Three standing figures for the title scene (made 2026-11-18): the boy from Warren, a sea captain and an old-time
diver. The scene, the boat, the computer and the boy's helmet are made elsewhere.

The user's words (2026-11-18): "the main menu / start of the game should be the boy from warren, a sea captain, and
and oldtimy diver on a shrimping boat (look up reference pics). In the open back cabin of the shrimping boat should
be a old timey franketstein computer hooked up to a helmet on the boys head- the controls for the pc are the
controls for the game".

## Files

- `tools/build_title_figures.py`: builds all three in Blender 4.3:
  `blender -b --factory-startup --python tools/build_title_figures.py`, then `godot --headless --path . --import`.
- `tools/blend/title_figures.blend`: the editable file, one collection per figure (`boy`, `captain`, `diver`).
  Re-running the script overwrites it.
- `models/title_boy.glb`, `models/title_captain.glb`, `models/title_diver.glb`.
- `scripts/title_figures.gd` (`TitleFigures`): makes and poses them.

## Using them

```
var boy := TitleFigures.boy()          # also captain(), diver()
add_child(boy)                         # stands at its origin, feet on y = 0, facing -Z; idles by itself
TitleFigures.head_node(boy).add_child(helmet)
TitleFigures.look_at_point(boy, screen.global_position)   # TitleFigures.look_about(boy) lets go
```

Each figure is a `TitleFigures.Idle` (a Node3D). Under it, `Model` is the imported glb, turned 180 degrees (the
models face +Z, as the boy's rig wants) and, for the adults, scaled by `ADULT_SCALE` (1.44). Its Skeleton3D has a
`BoneAttachment3D` called `HeadMount` on the bone `head`. Every frame the Idle poses a few bones itself:
breathing in the spine and chest, a slow sway, the boy's arms brought down from his T pose with the elbows a little
bent and the fingers curled, and the head turned (eased, held to what a neck can do) toward the point it was given,
or wandering slowly when it has none. The diver turns his whole top half instead, because his helmet is screwed to
his breastplate. Each mesh's `lod_bias` is 64, so the importer's automatic LODs never show.

### The boy's head, for the helmet

`TitleFigures.head_node(boy)` is `Boy/Model/boy_armature/Skeleton3D/HeadMount`. It sits on the head bone's joint, where
the head meets the neck: (0, 1.012, 0) above his feet when he stands straight. In its own frame +Y is up and **+Z is
the way he faces** (it is under the turned model). Measured from that joint, in that frame (metres, the boy at his
own size, 1.27 m to the top of his hair):

| | x (side to side) | y (up) | z (back to front) |
| --- | --- | --- | --- |
| head (skin) | -0.110 .. 0.110 | -0.049 .. 0.235 | -0.106 .. 0.119 |
| hair (bowl cut) | -0.119 .. 0.119 | 0.035 .. 0.247 | -0.126 .. 0.125 |

The top of his head is (0, 0.247, 0) on the hair and (0, 0.235, 0) on the skin. The middle of the skull is about
(0, 0.093, 0.006). A helmet to fit over his hair wants an inside of about 0.24 wide and 0.26 deep, its crown at least
0.25 above the joint. The bowl cut can be hidden (`boy_hair__bowl`, `boy_hairtop__bowl`) if the helmet should sit
lower.

## What each is made of

Triangles as exported. Heights as they stand in the scene.

### The boy: 6,093 triangles, 1.27 m

GameCommon's boy (`godot/character-controller`) turned out as Warren turns out its players (Warren's
`scripts/looks.gd`, `Looks.decode` for the first seat, and `Looks.apply`):

- the outfit `trousers` with its braces left off (`"over": "none"`); the trouser cut `tube` and boots `round`, both
  as made; no cap; face `base` (no face at all);
- the head is HeadShape's `inside_round` (Warren's `Looks.HEAD`). `head_shaped()` in the build script is
  `HeadShape._shaped` line for line, done once in Blender, not at run time;
- the cut of hair is `bowl` (Warren's `Looks.HAIR`);
- Warren's colours: shirt `SHIRTS[0]` (0.37, 0.19, 0.175), trousers (0.17, 0.17, 0.19), boots (0.17, 0.13, 0.1),
  skin (0.79, 0.65, 0.54), hair (0.2, 0.16, 0.13).

The skeleton and proportions are the boy's own: the build reads every joint out of the model and makes the armature
again with GameCommon's `make_armature` (every bone straight up and unrotated, as the boy's are). The body, hands and
boots come from GameCommon's `models/boy_tp.glb` (the boy collapsed for crowds). The head and the hair come from the
full `models/boy.glb`, because they are seen close. Warren's own `boy.glb` (2026-10-17) has the same skeleton,
and the same triangle counts in the parts used, as GameCommon's.

**Where he is not Warren's boy:**

- Warren draws his hair with ink-figure's `LockHair` (the cut `fringe`), not the modelled bowl cut. Here the bowl cut
  is shown instead, because ink-figure is not in Gulp.
- Warren's skin uses ink-figure's `skin_ink` shader, and the rig's toon shading. Here every figure has plain
  materials, as imported (roughness 1), in the right colours.

To match those too, install `godot/ink-figure` and dress him with `InkFigure.dress` / `LockHair.add_to`, as
Warren's `Looks.ink` does.

### The captain: 5,640 triangles, 1.83 m to the top of his cap

An old fishing-boat skipper: a navy peaked cap with a black peak and a brass cord, a white beard and moustache,
bushy brows, grey hair under the cap, a big nose, a cream roll-neck fisherman's jumper with a ribbed hem and cuffs,
dark trousers, tall black rubber sea boots with turned-down tops, and a short pipe in the left corner of his mouth.
He is one mesh, `captain`, with materials `captain_sweater`, `_trousers`, `_skin`, `_beard`, `_boots`, `_cap`,
`_peak`, `_pipe` and `_brass`. Beard, cap, peak, cord and pipe all follow the head bone.

### The diver: 6,708 triangles, 1.93 m to the top of his helmet

Standard diving dress, after the US Navy Mark V and Siebe Gorman's (shape only; nobody's model or texture):

- a spun-copper bonnet about 0.35 m across, as the Mark V's;
- four lights: the big front one, two at the sides behind guard bars, one at the top front. Each has a brass rim
  and dark glass;
- an exhaust valve low on his right;
- the air inlet's elbow at the back, with the black air hose running down his back to the deck. The hose lies on the
  deck 0.95 m behind him, its end at about (-0.2, 0.03, 0.95) from his feet, ready to run to a pump;
- a copper breastplate (corselet) whose edge rides up over the shoulders, a brass neck ring, and brass brails round
  its edge with eight wing nuts;
- lead weights hung front and back on studs;
- a tan rubberised canvas suit with baggy folds at elbows and knees, black rubber cuffs and bare hands;
- a leather belt with a brass buckle and a knife in its sheath on his right;
- canvas boots with lead soles, brass toe caps and bands.

He is one mesh, `diver`, with materials `diver_suit`, `_rubber`, `_skin`, `_copper`, `_brass`, `_glass`, `_lead`,
`_leather` and `_canvas`. Copper and brass are metallic, the glass glossy. The helmet, corselet, brass, glass and
weights all follow the chest bone, as the real helmet is locked to the breastplate. His head bone is there, but
nothing hangs on it.

### How the adults are built

They are made the way GameCommon's `tools/build_figure_template.py` makes a figure. They use `build_character.py`'s
`Builder` (tubes and ellipsoids, each garment melted into one surface and cut to a budget), its `make_armature` and
its `export`. That script is loaded in place from GameCommon, not copied. `kit.export` saves its files to a scratch
folder in the system temp (`title_figures_*`), and the script then gathers them into the one .blend. Each adult is
modelled 1.25 m tall, as the template asks, and stood at 1.44 times that. The skeleton keeps the boy's bone names and
the template's contract (legs as siblings under the hips, ankles 0.05 above the sole). The arms are modelled hanging
a little out from the body (the captain 18 degrees, the diver 22), which the contract allows, so standing needs
little bending. Skin weights are smooth steps across each joint, measured along the slanted arm.

## Why not the controller's rig

The brief said to install GameCommon's `character-controller` with `kit.sh` and use its rig. That was not done.
Gulp already has `class_name Player` (the fish, `scripts/player.gd`) and `class_name Dust` (`scripts/dust.gd`).
`kit.sh install` would leave those two files alone, and the controller's `character_rig.gd`, which needs its own
`Player` (`Player.State`, `Player.Landing`...), would then fail to compile in Gulp. So nothing of the component was
installed. The figures are on its skeleton and built with its Blender kit, and `TitleFigures.Idle` poses them itself
(about 40 lines). If CharacterRig is wanted later, one of the two `Player` classes must be renamed first.

## Checks run (2026-11-18)

- **Renders** in Blender (workbench) of each figure from the front, the back, both sides, a quarter and above, and
  close on the head (front, side, back) and a hand. **Godot pictures** (a window kept off screen, silent) of the
  three standing posed, from the front, the back, both sides, above and a quarter, close on each head (front, side,
  back, above) and hand, and again with all three turned to look at a point up and to their right. All were looked
  at. Fixed from them: the adults' shoulders standing up square out of the jumper and the suit; the suit poking out
  through the corselet at the shoulders; the light rims drawn as solid discs over the glass; the boy's collapsed hair
  going ragged (now the full one); the suit showing through the cuffs.
- **Clipping, measured** in Blender (rest pose, ray parity against each closed part):
  - nothing of the captain's head or hair comes through his cap (0 of 59 and 0 of 11 points);
  - his peak does not touch his head or brows;
  - his pipe does not enter his head. It sits up to 9 mm into his beard and moustache, as a pipe held in the mouth
    does;
  - his beard sits up to 18 mm into the front of the roll neck (13 of 306 points), resting on the collar;
  - no trouser comes through the jumper or the boots;
  - the diver's suit does not come through the copper above the corselet's edge (0 of 106) or through his cuffs;
  - the weights clear the suit;
  - the boy's scalp shows through the hair at 1 point of 325, by 1.3 mm.

  In the posed pictures, turning the heads put no beard through a collar and no helmet through anything.
- **Winding:** in Godot, every surface of the three .glb files has its triangles wound with its normals (WINDING
  OK). The boy's boots and the captain's head and beard have 2 near-degenerate triangles each. In Blender, every
  closed piece faces out (ray parity), except the diver's four light rims. Each rim is a tube bent round and closed on
  itself, so its two rounded ends lie inside each other: those faces are hidden inside the rim, and Godot's check
  shows their winding agrees with their normals.
- **Headless run:** a scratch script made all three with TitleFigures, added them to a tree, and stepped them 300
  frames, with no errors. The boy's and the diver's heads turned to the point given (the boy's `HeadMount` faced it
  to within a degree).
- **Gulp's smoke test** (`sh tests/smoke.sh`): GULP SMOKE PASSED.

## Not verified

- Not seen in the title scene, under its light, on the boat, or under Gulp's post shader; not on a phone.
- The boy's helmet is not made, so it has not been tried on him.
- Nobody has watched the idle moving for long. It was checked only in stills and by numbers. There is no
  SHAKE-style check of the bones.
- Over the brief's budget of 3,000 to 6,000 triangles: the boy is at 6,093 and the diver at 6,708 (his brass
  fittings take about 2,200). Only the captain (5,640) is inside it. Detail is spent fairly evenly within each part,
  not concentrated at faces and edges as on the Twilight Princess reference models.

## Whose calls

The user's: the boy from Warren, a sea captain, an old-time diver, on a shrimp boat, the boy in a helmet wired to a
computer (2026-11-18).

Claude's picks, all changeable:

- the routes taken:
  - the boy built in Blender from GameCommon's boy models;
  - the bowl cut and plain materials standing in for Warren's ink hair and skin;
  - the controller's rig not installed, for the class-name clash above;
- the captain's dress: the peaked cap rather than a sou'wester, the cream roll-neck jumper rather than a pea coat,
  black sea boots, the white beard and the pipe;
- the diver details:
  - the Mark V helmet shape, with Siebe Gorman-style chest and back weights (as the brief listed);
  - eight wing nuts;
  - the valve on his right;
  - the hose lying behind him;
  - no face behind the glass;
- the poses and the idle: the boy standing with his arms at his sides, breathing, swaying and glancing about; the
  diver turning his top half to look;
- all colours apart from the boy's, which are Warren's.

## For GameCommon (not changed here)

- `build_character.py`'s `export` writes under its own `ROOT` and always exports vertex colours (`ACTIVE`). A game
  using the kit in place must point `kit.ROOT` elsewhere and export again. A `root` argument and a choice of vertex
  colours would make that cleaner.
- `character_rig.gd` names the controller's `Player` class directly. In a game with a `Player` of its own (Gulp), the
  component cannot be installed as it is.
