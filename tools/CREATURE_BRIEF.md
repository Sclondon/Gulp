# Brief: building sea creatures for GameCommon (used first in Gulp)

You are building shared creature components in `C:\Projects\GameCommon\godot\<name>` for the user's Godot 4.7
games. They are used first in **Gulp** (`C:\Projects\FrontRangeInstituteGames\Gulp`: a 3D eat-and-grow sea game,
GL Compatibility, phones and a web build), which the main session is wiring up at the same time. The user asked
for these animals on 2026-11-17 in one list: "blue fin tuna, blue marlin, mahi mahi, wahoo, barracuda, sea bass,
mackerel, big eye tuna, grouper, snapper, rockfish, perch, pacific bonito, blue shark, leopard shark, kelp bass,
garibaldi, halibut, anchovy, rays, lobsters, shrimp, crabs", then "a nudibranch" and "garden eels", and: "the fish
should be able to open their mouths". The sea is a California-like coast (kelp forest, rocky reef, sea grass,
sand flats, an open ocean shelf), so where the user's word is loose, pick the Californian species.

You own ONLY the component folders named in your task. Do not edit any other component, GameCommon's top README,
or any game. GameCommon has no git, and other agents are working in sibling folders right now.

## The pattern to copy

Finished examples (read one fully before starting: README.md, FILES.txt, the .gd, the .gdshader, the build
script, example.gd and the check script):

- `C:\Projects\GameCommon\godot\yellowfin-tuna` : the base pattern (a stiff fast fish).
- `C:\Projects\GameCommon\godot\sardine` : a small fish, with a third very light vertex-coloured "school" mesh for
  drawing hundreds in one MultiMesh (`school_mesh()`, `mesh_of()`, `new_material()` statics).
- `C:\Projects\GameCommon\godot\sailfish` and `swordfish` : big fish with a bill.
- `C:\Projects\GameCommon\godot\sockeye-salmon` : one build script and one shader making several models
  (variants), and a **lower jaw that works** (`gape`).
- `C:\Projects\GameCommon\godot\moray-eel`, `giant-squid`, `sea-nettle`: bodies that are simulated ropes.

Also load the `blender-models` skill and read `~/.claude/skills/godot-checks/SKILL.md` and its `GOTCHAS.md`.

One component per species unless your task says otherwise, each laid out like the tuna's:

- `files/creatures/<snake_name>/<snake_name>.gd` with a `class_name` (CamelCase of the species). The same driving
  names as `YellowfinTuna` wherever they make sense: consts `LENGTH`, `DEPTH`, `WIDTH` (metres at scale 1, life
  size); `beat`, `tail_beats`, `sway`, `low`, `phase`; `step(velocity, delta)`; `set_shader_parameter(name, value)`;
  `material()`; statics `mesh_of(low := false) -> Mesh` and `new_material() -> ShaderMaterial`.
- Its nose points to -Z, up is +Y, **its origin is on its middle line half way along its length** (for a bottom
  animal that walks, the origin is on the ground under its middle: say so in the README).
- Everything that moves is a function of `phase` only (no `TIME`, no clock of its own), so it loops exactly.
- Shader settings every fish must have:
  - `curl`: bends the body round to one side behind the head, radians from gills to tail; more than 0 and the tail
    comes round to +X (as the tuna's).
  - **`gape`**: 0 the mouth shut, 1 wide open, as when it bites. The lower jaw must really swing down about its
    hinge (and the upper jaw lift or push out a little if the species does that), showing a dark mouth inside:
    build the jaw and the inside of the mouth into the model, and turn the jaw in the vertex shader (see how the
    sockeye salmon does it: `hinge_s`, `hinge_y`, `gape`). Also a property `gape` on the node that sets it. This
    is the user's ask ("the fish should be able to open their mouths"): check it in pictures, open and shut,
    from the side and the front.
- `<snake_name>.gdshader`: all markings drawn in the shader (no texture files); the swimming bend in the vertex
  shader, in the way that species swims. It must run in **GL Compatibility** (nothing that needs Forward+). One
  opaque draw with back faces culled where possible.
- `models/<snake_name>.glb` (full: 20-60 thousand triangles depending on size; small animals less) and
  `models/<snake_name>_lo.glb` (a tenth of that or less), built by `tools/build_<snake_name>.py` in Blender 4.3
  background mode, which also saves the editable `tools/<snake_name>.blend`; a `tools/.gdignore`.
- `example.gd`, `FILES.txt`, `README.md` (the tuna's sections: what it is, what it follows, using it, files,
  checked, limits; the user's words that asked for it; which choices were Claude's), and beside the README (not
  installed) a check script like `tuna_check.gd` and one still PNG.

No reference pictures were given: work from what the species looks like, and trace or copy nothing. Each animal
must be recognisable as its species, not a generic fish: get the proportions, fin layout and markings right.

## The user's rules here

- Models are built in Blender by a script (never meshes generated in Godot code). Render each model from four
  sides (and above, below, close on the head) and LOOK at the pictures yourself (Read the PNGs) before calling it
  done; fix what looks wrong.
- Check for inside-out faces in code as well as by eye: the build script prints a `WINDING` line (as the tuna's
  does), and the check script reads every triangle of the imported models back in Godot (Godot's front faces wind
  clockwise as seen).
- Blender: `"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" --background --python <script>`.
  Godot 4.7: `"C:\Program Files (x86)\Steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe"`.
  Neither is on PATH. There is no system Python.
- Every Godot run: `--audio-driver Dummy` and `</dev/null`. Prefer `--headless`. A real window only when pictures
  need one: short, off to one side (`--position 2600,60`), and make sure that Godot process has ended afterwards
  (killing the shell does not close Godot on Windows: check with `tasklist`, and `taskkill` only a PID that is
  yours; other sessions have Godot editors and tests open, never close those). Never leave anything running.
  Give every run a `timeout`. Run `--headless --import` before the first run of a project.
- Test in a scratch Godot project of your own (GL Compatibility) in a new folder under
  `C:\Users\stewa\AppData\Local\Temp\claude\be065d617517d416\9790e32c-36f1-4aaf-8ece-7f095c2906fe\scratchpad\<your component name>`,
  installing with `sh /c/Projects/GameCommon/kit.sh install godot/<name> <project>`. Never in a game.
- No `rm` in shell commands (write to new folders instead). Write files with the Write tool, not shell heredocs.
- Many agents are building at once on this machine: do not run more than one Blender or one Godot at a time.

## Your report

Brief. For each component: the class name, its public names and settings, LENGTH/DEPTH/WIDTH and how far fins
reach, triangle counts, anything unusual about driving it (origin, extra settings); what you checked and how; what
is not verified; limits.
