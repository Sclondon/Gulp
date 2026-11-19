"""Hair, beards and moustaches for Gulp's three figures, as layered painted lock cards.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup \
        --python tools/build_hair.py -- brother|boy|captain|all

Writes models/hair/<figure>_<piece>.glb, textures/hair/<figure>_locks.png and tools/blend/hair/<figure>.blend.
Look at them with tests/hair_view.gd (lit, perspective, seven angles, beside the concept sheet).

DECISION (Claude's pick, 2026-11-18)
What: every mass of hair (a head of hair, a beard, a moustache, brows) is
  1. a dark UNDER-SHELL: the figure's own head surface pushed out part of the way to the hair's outside, so no scalp
     or chin shows between locks and the gaps read as deep hair, not skin; its last row is a band of pointed strands,
     so where it meets the skin (the hairline, the nape, the beard's cheek line) it breaks into hair, not an edge;
  2. two or three LAYERS of alpha-tested CARDS (strips of 12 triangles), each carrying one PAINTED LOCK from a small
     atlas (a clump with its own light middle, dark edges, strands and ragged pointed tips; curls for the older
     brother, tapered locks for the boy, wavy clumps for the captain), rooted under the layer above, combed along a
     flow field (from a crown, falling with gravity) and lifted off the head toward their tips, so the outline
     breaks into clumps;
  3. the cards' NORMALS taken from a smooth HULL (the outside of the hair as one soft volume) instead of each card's
     own face, so every card shades as part of one rounded mass: one light side and one shadow side across the whole
     head, no card-edge steps. Deep layers are darker (vertex colour), roots darker than tips.
  Each figure's head is read from its .glb at build time (its own surface by rays from the head's middle, with the
  ears filtered out), so the hair follows the heads as they are rebuilt; nothing is placed by hard-coded positions
  except in angles round the head. Pieces are in the figure's model space at rest: attach each under a
  BoneAttachment3D on `head` (tests/hair_view.gd shows how). Beard and moustache are separate pieces so they can go
  to a `jaw` bone later.
Why: the captain's earlier rounds tried separate cards with the inked shader (read as flat white shingles from the
  side: each card shaded by its own face, so every edge was a step) and one smooth shell with painted bands (read as a
  slab or a plate: no broken outline). Cards with painted alpha locks give the broken outline; normals from one hull
  give the single soft mass; the dark under-shell gives depth between clumps.
The practice it follows: game hair cards with alpha test (alpha-clipped cards for stable outlines, no sorting), layered
  from a dark base layer out; normals transferred or projected from a "blob" hull mesh so the cards shade as a volume
  (Blender's Data Transfer, "normal thief" tools: the usual fix for faceted card shading, Polycount and the Conan
  Exiles art wiki); hand-painted lock textures in place of baked strands for a stylised look (Twilight Princess, Wind
  Waker-era and Genshin-style hair are a modelled shell or chunky locks with painted texture).
Alternatives: a modelled shell or chunky locks alone (Twilight Princess: cheap, but its outline is smooth; the user's
  sheets show broken curls and ragged beards), many thin strand cards (a realistic look, thousands of triangles,
  sorting), shell fur (many layers drawn again: far too heavy for phones in GL Compatibility), Blender hair curves
  (not exportable to a game as they are).
Shader: shaders/hair_cards.gdshader (new, alpha cut by hand, two-sided with the hull's normal kept on back faces).

FOURTH PASS (2026-11-18): SOFT. The third pass read as wood chips (the brother) and paper flakes (the captain).
  - The brother's mop: MODELLED LOCKS as soft arches (Builder.lock: four points across, thick in the middle, the edges
    tucked down into the mass, 5 or 6 rows along, a tapered rounded point that rolls over), their normals the arch's own
    blended 60% toward the smooth hull's, so the mop lights as one soft mass with the curls as a secondary rhythm. 48
    locks, combed: each region (nape, back, crown, sides, upper ring, top, fringe) shares one comb and one sideways
    bend, with only 4 degrees of jitter at the root, so neighbours lie nearly parallel; the top, crown, back and fringe
    curls roll UNDER (the bend of each C makes the outline), the nape flicks out a little. A warm dark-brown under-shell
    near the locks' own shade (no black holes), ending above the hairline so its edge never shows. Dark brown palette;
    the amber-red is only the shader's sheen. The moustache: one thin soft shell on the upper lip, no cards.
  - The captain's beard, moustache, brows and fringe: ONE smooth shell per mass (hull normals), painted with low-contrast
    soft strokes; its edges a SOFT band (paint_lock's `soft`: the alpha falls off in a few broad points) that the
    shader's dithered cut (`feather`) turns into a soft edge; only a few large soft-edged cards (6 on the beard, 6 on
    the brows, none on the moustache or the fringe). The moustache is its own drooping pillow, thicker than the beard
    where they meet, closed to the skin at its top and sides, a soft shadow on the beard under it (`shade_at`).
  - The boy: soft tips (`soft`, `side_soft`), a lighter, cooler golden palette.

JAW: WHAT EACH POINT FOLLOWS (for tools/face_rig.py's bind_to_face). A mass with a `jaw` function (head-frame angles
  from that mass's own middle -> 0..1) writes, in its .blend object and its glb:
    vertex groups `follow_jaw` (the weight) and `follow_head` (1 - the weight), and a point attribute `_JAW` (the same
    weight; exported to the glb as the custom attribute _JAW).
  1 = ride the jaw (open with the mouth), 0 = ride the head (the upper lip and the cheeks above the jaw). Now:
    captain_beard: 1 under and round the chin and along the jaw, fading to 0 up the cheeks (above about 14 degrees
      from the jaw's middle) and back along the sideburns (|azimuth| 72 to 100);
    captain_moustache, brother_moustache: 0 everywhere (the upper lip: the head, or the upper lip's own shapes);
    brows and hair: no `jaw` (the head).
  The face builder can use it in place of (or to scale) the nearest-skin weights bind_to_face copies: for a beard
  point, jaw weight = _JAW, head weight = 1 - _JAW; its shape-key moves are still taken from the nearest skin.
"""

import bpy
import bmesh
import copy
import math
import os
import random
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATLAS = 512
TW, TH = 128, 256  # one lock tile: 4 across, 2 down


def lerp(a, b, t):
    return a + (b - a) * t


def sstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def pw(keys, x):
    """Piecewise linear through (x, y) keys."""
    if x <= keys[0][0]:
        return keys[0][1]
    for (x0, y0), (x1, y1) in zip(keys, keys[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return keys[-1][1]


def direction(a, e):
    """Head frame: azimuth a (degrees, 0 = the face, + toward the figure's left, +X), elevation e (degrees)."""
    a, e = math.radians(a), math.radians(e)
    return Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)))


def angles(d):
    d = d.normalized()
    return math.degrees(math.atan2(d.x, -d.y)), math.degrees(math.asin(max(-1.0, min(1.0, d.z))))


# ---------------------------------------------------------------------------------------------------------------------
# The head, read from the figure's glb


class Head:
    STEP = 4.0

    def __init__(self, fig):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "models", fig + ".glb"))
        # (the body, and the head when tools/face_rig.py has split it off into a mesh of its own)
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys, hv = [], [], []
        for name in (fig + "_body", fig + "_head"):
            body = bpy.data.objects.get(name)
            if body is None or body.type != "MESH":
                continue
            me = body.evaluated_get(dg).to_mesh()
            mw = body.matrix_world
            base = len(verts)
            vs = [mw @ v.co for v in me.vertices]
            verts += vs
            polys += [tuple(base + i for i in p.vertices) for p in me.polygons]
            if "head" in body.vertex_groups:
                g = body.vertex_groups["head"].index
                hv += [vs[v.index] for v in body.data.vertices
                       if any(x.group == g and x.weight > 0.5 for x in v.groups)]
        self.bvh = BVHTree.FromPolygons(verts, polys)
        # (the cap, when the figure wears one: hair under it is kept inside it)
        self.cap = None
        cap = bpy.data.objects.get(fig + "_cap")
        if cap is not None and cap.type == "MESH":
            cm = cap.evaluated_get(dg).to_mesh()
            cv = [cap.matrix_world @ v.co for v in cm.vertices]
            self.cap = BVHTree.FromPolygons(cv, [tuple(p.vertices) for p in cm.polygons])
        nose = min(hv, key=lambda p: p.y)
        top = max(p.z for p in hv)
        crown = [p for p in hv if p.z > nose.z]
        self.c = Vector((0.0, (min(p.y for p in crown) + max(p.y for p in crown)) / 2, nose.z + 0.25 * (top - nose.z)))
        self.size = top - nose.z  # nose to crown, the scale every figure's numbers are in
        self.nose = angles(nose - self.c)
        front = [p for p in hv if abs(p.x) < 0.015 and p.y < self.c.y]
        self.chin = angles(min(front, key=lambda p: p.z) - self.c)
        self._rays()
        print("HAIR head", fig, "centre", tuple(round(x, 3) for x in self.c), "size", round(self.size, 3),
              "nose", [round(x) for x in self.nose], "chin", [round(x) for x in self.chin])

    def recentred(self, dy, dz, reach=None):
        """The same head read from another middle (dy back, dz up, in head sizes): a beard is read from the jaw's
        middle, where rays meet the jaw, the chin's underside and the throat instead of passing under them. reach (head
        sizes): no skin further than that from the middle, so below the chin, where the rays go on to the throat and the
        chest, the beard closes into a rounded mass instead of hanging down the chest."""
        h = copy.copy(self)
        h.c = self.c + Vector((0.0, dy * self.size, dz * self.size))
        h.limit = reach * self.size if reach else None
        h._rays()
        return h

    def _rays(self):
        reach = getattr(self, "limit", None) or 2.2 * self.size
        na, ne = int(360 / self.STEP), int(180 / self.STEP) + 1
        s = np.zeros((ne, na))
        for i in range(ne):
            for j in range(na):
                d = direction(-180 + j * self.STEP, -90 + i * self.STEP)
                # (the furthest skin within reach: rays from inside meet the mouth's pocket and the eyes first)
                o, far, n = self.c.copy(), 0.0, 0
                while n < 8:
                    hit = self.bvh.ray_cast(o, d, reach - (o - self.c).length)
                    if hit[0] is None:
                        break
                    # (but not on to the next body part: below the jaw a ray leaves the head and meets the chest)
                    if far > 0 and (hit[0] - self.c).length > far + 0.04:
                        break
                    far = (hit[0] - self.c).length
                    o = hit[0] + d * 1e-4
                    n += 1
                if getattr(self, "limit", None):
                    far = min(far, reach) if far > 0 else reach
                s[i, j] = far if far > 0 else (s[i - 1, j] if i else self.size)
        # (an opening, the smallest then the largest over 24 degrees round and 12 up, takes the ears out; then a blur)
        def roll_min(x, k, ax):
            return np.min([np.roll(x, r, axis=ax) for r in range(-k, k + 1)], axis=0)

        def roll_max(x, k, ax):
            return np.max([np.roll(x, r, axis=ax) for r in range(-k, k + 1)], axis=0)

        o = roll_max(roll_max(roll_min(roll_min(s, 3, 1), 1, 0), 3, 1), 1, 0)
        for _ in range(2):
            o = (o * 2 + np.roll(o, 1, 1) + np.roll(o, -1, 1)) / 4
            o[1:-1] = (o[1:-1] * 2 + o[:-2] + o[2:]) / 4
        self.raw, self.s = s, o

    def _grid(self, arr, a, e):
        x = ((a + 180.0) % 360.0) / self.STEP
        y = min(max((e + 90.0) / self.STEP, 0.0), arr.shape[0] - 1.001)
        j0, i0 = int(x) % arr.shape[1], int(y)
        j1 = (j0 + 1) % arr.shape[1]
        fx, fy = x - int(x), y - i0
        top = arr[i0, j0] * (1 - fx) + arr[i0, j1] * fx
        bot = arr[i0 + 1, j0] * (1 - fx) + arr[i0 + 1, j1] * fx
        return top * (1 - fy) + bot * fy

    def skin(self, d):
        """The head's surface along a direction, ears filtered out (distance from the middle)."""
        a, e = angles(d)
        f, r = self._grid(self.s, a, e), self._grid(self.raw, a, e)
        # (the filter also shaves the cheekbones and temples a little: keep the true skin wherever nothing sticks out
        # more than a centimetre, which is everywhere but the ears)
        return lerp(max(r, f), f, sstep(0.008, 0.016, r - f))

    def skin_raw(self, d):
        a, e = angles(d)
        return self._grid(self.raw, a, e)


# ---------------------------------------------------------------------------------------------------------------------
# Painting the lock atlas


def palette(tone, pal):
    stops = [0.0, 0.35, 0.62, 0.86, 1.0]
    tone = np.clip(tone, 0.0, 1.0)
    out = np.zeros(tone.shape + (3,))
    for k in range(3):
        out[..., k] = np.interp(tone, stops, [c[k] for c in pal])
    return out


def paint_lock(img, tile, pal, rng, length=0.95, width=0.8, curl=0.0, curl_start=0.5, bend=0.0, wave=0.0,
               rag=0.3, strands=9, light=0.6, base=False, gloss_at=0.45, taper=0.85, tufts=3, curly=False, strokes=False,
               soft=0.0, points=2.0, brighten=0.0, side_soft=0.55):
    """One lock in a 128 x 256 tile: root at the top, tip toward the bottom. curl: radians it turns past curl_start
    (a hook), bend: a slow lean, wave: an S. base: a band of strands across the whole tile (the under-shell's edge)."""
    x0, y0 = (tile % 4) * TW, (tile // 4) * TH
    yy, xx = np.mgrid[0:TH, 0:TW].astype(float)
    sr = rng.random(64)
    ends = rng.random(64)
    if base:
        k = (xx / TW * strands * 2).astype(int)
        frac = xx / TW * strands * 2 - k
        t = yy / TH
        end = 1.0 - rag * ends[k % 64]
        zone = 0.3
        f = np.clip((t - (end - zone)) / zone, 0, 1)
        alpha = ((t < end) & (np.abs(frac - 0.5) * 2 < 1.0 - f)).astype(float)
        if soft > 0.0:
            # (a SOFT band (fourth pass): no strands, the alpha falls off smoothly toward the edge, its end wavering in
            # a few broad soft points; the shader's dithered cut (feather) turns it into a soft edge, not spikes)
            ph = rng.uniform(0, 2 * math.pi, 2)
            u = xx / TW
            end = 0.98 - rag * (0.5 + 0.35 * np.sin(u * 2 * math.pi * points + ph[0])
                                + 0.15 * np.sin(u * 2 * math.pi * points * 2.3 + ph[1]))
            alpha = np.clip((end - t) / soft, 0, 1) ** 1.2
        alpha[t < 0.5] = 1.0
        tone = 0.42 + 0.14 * (sr[k % 64] - 0.5) + 0.08 * np.sin(frac * math.pi) - 0.08 * (1 - t)
        if curly:
            # (a mass of small curls: crescents of light, each with its shadow inside, over a dark ground)
            tone = 0.36 + 0.06 * (sr[k % 64] - 0.5)
            for _ in range(70):
                cx, cy = rng.uniform(0, TW), rng.uniform(0, TH * 0.75)
                r = rng.uniform(7, 15)
                a0 = rng.uniform(0, 2 * math.pi)
                dd = np.hypot(xx - cx, yy - cy)
                ang = np.mod(np.arctan2(yy - cy, xx - cx) - a0, 2 * math.pi)
                arc = (ang < 3.6) * np.sin(np.clip(ang / 3.6, 0, 1) * math.pi)
                tone = tone + 0.3 * arc * np.clip(1 - np.abs(dd - r) / 2.6, 0, 1)
                tone = tone - 0.1 * arc * np.clip(1 - np.abs(dd - r + 4) / 3, 0, 1)
        if strokes:
            # (a painted beard: soft long clumps, each lighter down its middle with a shadow under its end, over a
            # mid ground; low contrast, as the head sheet paints it)
            tone = 0.5 + 0.04 * (sr[k % 64] - 0.5)
            for _ in range(60):
                cx, cy = rng.uniform(0, TW), rng.uniform(-20, TH * 0.6)
                ln, wd = rng.uniform(40, 80), rng.uniform(9, 15)
                lean = rng.uniform(-0.25, 0.25)
                v = (yy - cy) / ln
                u = (xx - cx - lean * (yy - cy)) / wd
                half = np.clip(1 - v, 0, 1) ** 0.6 * (v > 0)
                inside_s = np.abs(u) < half
                body = np.clip(1 - np.abs(u) / np.maximum(half, 1e-3), 0, 1)
                tone = np.where(inside_s, 0.48 + 0.12 * body * np.clip(1.2 - v, 0, 1), tone)
                tone = tone - 0.04 * ((v > 1.0) & (v < 1.15) & (np.abs(u) < 0.5))
        tone = tone + brighten
        rgb = palette(tone, pal)
    else:
        n = 120
        ts = np.linspace(0.0, 1.0, n)
        h = bend * ts + curl * np.clip(ts - curl_start, 0, None) ** 1.25 / max(1 - curl_start, 1e-3) \
            + wave * np.sin(ts * math.pi * 2.0)
        step = length * TH / n
        px = np.cumsum(np.sin(h) * step) - np.sin(h[0]) * step
        py = np.cumsum(np.cos(h) * step) - np.cos(h[0]) * step
        hw = width * TW / 2 * (1.0 - taper * ts ** 1.6)
        # (fit inside the tile, root at the top middle)
        span_x = (px - hw).min(), (px + hw).max()
        span_y = py.max() + 4
        sc = min(1.0, (TW - 6) / (span_x[1] - span_x[0]), (TH - 8) / span_y)
        px, py, hw = px * sc, py * sc, hw * sc
        px += TW / 2 - (span_x[0] + span_x[1]) / 2 * sc
        py += 3
        tx, ty = np.gradient(px), np.gradient(py)
        tl = np.hypot(tx, ty)
        tx, ty = tx / tl, ty / tl
        dx = xx[..., None] - px[None, None, :]
        dy = yy[..., None] - py[None, None, :]
        dist = dx * dx + dy * dy
        i = np.argmin(dist, axis=2)
        cx, cy = px[i], py[i]
        ux, uy = tx[i], ty[i]
        q = (xx - cx) * ux + (yy - cy) * uy
        d = -(xx - cx) * uy + (yy - cy) * ux
        t = ts[i]
        w = hw[i]
        s = d / w
        inside = (np.abs(s) < 1.0) & ~((i == n - 1) & (q > 0.5)) & ~((i == 0) & (q < -0.5))
        k = np.clip(((s + 1) / 2 * strands).astype(int), 0, strands - 1)
        frac = (s + 1) / 2 * strands - k
        # (the tip breaks into a few pointed tufts, each ending at its own length: not single hairs, which read as
        # a comb)
        nt = tufts
        kt = np.clip(((s + 1) / 2 * nt).astype(int), 0, nt - 1)
        ft = (s + 1) / 2 * nt - kt
        end = 1.0 - rag * ends[kt]
        zone = 0.35
        f = np.clip((t - (end - zone)) / zone, 0, 1)
        alpha = (inside & (t <= end) & (np.abs(ft - 0.5) * 2 < 1.0 - f ** 1.3)).astype(float)
        # (soft edge, a pixel wide)
        alpha *= np.clip((1.0 - np.abs(s)) * w, 0, 1)
        if soft > 0.0:
            # (a SOFT lock (fourth pass): no tufts; the alpha falls off smoothly toward its sides and its tapered tip,
            # so with the shader's dithered cut the lock's outline is a big soft point, not a razor-cut flake)
            alpha = ((np.abs(s) < 1.0) & ~((i == 0) & (q < -0.5))).astype(float) \
                * np.clip((1.0 - np.abs(s)) / side_soft, 0, 1) * np.clip((1.0 - t) / soft, 0, 1) \
                * np.clip((1.0 - ((i == n - 1) & (q > 0)) * q / 6.0), 0, 1)
        tone = 0.4 + 0.28 * (1 - s * s) + 0.1 * (sr[k] - 0.5) - 0.1 * (1 - np.sin(frac * math.pi)) ** 4
        # (a dark groove where two tufts part)
        tone -= 0.18 * np.clip(1 - np.abs(ft - 0.5) * 2 - 0.75, 0, 1) * 4 * np.clip((t - 0.4) / 0.3, 0, 1) \
            * (np.abs(s) < 0.9)
        tone -= 0.15 * (1 - np.clip(t / 0.3, 0, 1)) ** 2
        tone -= 0.06 * t
        side = -1.0
        if curl != 0.0:
            inner = s * math.copysign(1.0, curl)
            side = -math.copysign(1.0, curl)
            c = np.clip((t - curl_start) / max(1 - curl_start, 1e-3), 0, 1)
            tone -= 0.22 * inner * c
        # (the light along the outer arc of the lock, as the sheet paints the copper on the curls)
        gl = np.exp(-((s - side * 0.35) / 0.32) ** 2) * np.clip((t - 0.12) / 0.2, 0, 1) * np.clip((0.92 - t) / 0.25, 0, 1)
        gl *= np.exp(-((t - gloss_at) / 0.35) ** 2)
        tone += light * 0.42 * gl * (0.75 + 0.5 * sr[k])
        rgb = palette(tone, pal)
    img[y0:y0 + TH, x0:x0 + TW, :3] = rgb
    img[y0:y0 + TH, x0:x0 + TW, 3] = alpha


def paint_surface(img, tile, pal, rng, grooves=4.0, lo=0.38, hi=0.62, streak=0.06):
    """The skin of a modelled lock (its light and shade come from the lock's shape and the vertex colour): a soft
    mid tone across the ribbon with a few broad strand grooves running its length, low in contrast; opaque."""
    x0, y0 = (tile % 4) * TW, (tile // 4) * TH
    yy, xx = np.mgrid[0:TH, 0:TW].astype(float)
    u, v = xx / TW, yy / TH
    ph = rng.uniform(0, 2 * math.pi, 3)
    # (the grooves wander a little along the lock, so they read as clumps of strands, not ruled lines)
    w = u + 0.03 * np.sin(v * 7.0 + ph[0]) + 0.02 * np.sin(v * 13.0 + ph[1])
    g = 0.5 + 0.5 * np.cos(w * grooves * 2 * math.pi)
    tone = lerp(lo, hi, g ** 1.5) + streak * blur(rng.random((TH, TW)), 4) * 4 - streak * 2
    # (darker toward the edges, as a ribbon turns away)
    tone -= 0.12 * (np.abs(u - 0.5) * 2) ** 2
    img[y0:y0 + TH, x0:x0 + TW, :3] = palette(tone, pal)
    img[y0:y0 + TH, x0:x0 + TW, 3] = 1.0


_SHEETS = {}


def sheet(name):
    """A concept sheet as an array (rows from the top, RGB 0..1), loaded once."""
    if name not in _SHEETS:
        im = bpy.data.images.load(os.path.join(HERE, "art_src", name))
        w, h = im.size
        _SHEETS[name] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3].copy()
    return _SHEETS[name]


def blur(x, r):
    """A box blur r pixels each way, three times (near a gaussian), edges held."""
    for _ in range(3):
        for ax in (0, 1):
            p = np.pad(x, [(r, r) if a == ax else (0, 0) for a in range(x.ndim)], mode="edge")
            c = np.cumsum(p, axis=ax)
            c = np.concatenate([np.zeros_like(np.take(c, [0], axis=ax)), c], axis=ax)
            n = x.shape[ax]
            x = (np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / (2 * r + 1)
    return x


KEYS = {
    # (which pixels of a sheet are hair: the light grey ground and the skin are not)
    # dark brown curls: darker than the skin and the ground
    "dark": lambda c: sstep_np(0.52, 0.44, lum(c)),
    # blond: yellow, its blue well under its red (the pink skin keeps more blue, the ground nearly all)
    "blond": lambda c: sstep_np(0.7, 0.64, c[..., 2] / np.maximum(c[..., 0], 1e-3)) * sstep_np(0.9, 0.82, lum(c)),
    # white-grey: low colour, warm or neutral (the ground is cool blue-grey), not the pink skin, not too dark
    "grey": lambda c: sstep_np(-0.035, -0.005, c[..., 0] - c[..., 2]) * sstep_np(0.11, 0.07, c[..., 0] - c[..., 2])
    * sstep_np(0.3, 0.4, lum(c)),
}


def lum(c):
    return c[..., 0] * 0.3 + c[..., 1] * 0.55 + c[..., 2] * 0.15


def sstep_np(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sample(src, x, y):
    """Bilinear sample of src (rows from the top) at pixel coordinates x, y (arrays)."""
    h, w = src.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    a, b = src[y0, x0], src[y0, x0 + 1]
    c, d = src[y0 + 1, x0], src[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def lift(img, tile, src, at, length, tip=0.0, width=0.5, key="dark", region=(0.0, 1.0), solid=False, lift_to=0.55,
         flat=0.85, side=0.88, gain=1.0, warm=(1.0, 1.0, 1.0), taper=0.0):
    """A lock LIFTED FROM THE CONCEPT SHEET into a tile (or part of one: region, the share of the tile's height):
    a strip of the painting `length` sheet pixels long (`width` of that across), centred at `at` (x, y in the sheet's
    own pixels, from its top left), its tip toward `tip` degrees (0 down the sheet, 90 to the right, -90 to the left,
    180 up), turned so the root is at the top of the tile and the tip at the bottom. The hair is cut from the ground
    and the skin by `key`, so the tip keeps the painting's own ragged outline; the sides fade (`side`) so a cut
    neighbour does not leave a straight edge. The painting's broad light and shade is taken out (`flat`: its large
    blur is divided away and replaced by `lift_to`), so the mass is shaded by the game's light, while its strokes,
    curls and colour stay. solid: no cut (an inside patch, for the under-shell)."""
    pic = sheet(src)
    x0, y0 = (tile % 4) * TW, (tile // 4) * TH
    r0, r1 = int(region[0] * TH), int(region[1] * TH)
    hh = r1 - r0
    vv, uu = np.mgrid[0:hh, 0:TW].astype(float)
    a = math.radians(tip)
    tx, ty = math.sin(a), math.cos(a)
    px_, py_ = math.cos(a), -math.sin(a)
    along = ((vv + 0.5) / hh - 0.5) * length
    across = ((uu + 0.5) / TW - 0.5) * length * width
    sx = at[0] + along * tx + across * px_
    sy = at[1] + along * ty + across * py_
    # (supersampled 2 x 2: the sheet's pixels are finer than the tile's along the lock)
    rgb = np.zeros((hh, TW, 3))
    for ox in (-0.25, 0.25):
        for oy in (-0.25, 0.25):
            dl, dc = oy * length / hh, ox * length * width / TW
            rgb += sample(pic, sx + dl * tx + dc * px_, sy + dl * ty + dc * py_) / 4
    if solid:
        alpha = np.ones((hh, TW))
    else:
        alpha = KEYS[key](rgb)
        s = np.abs((uu + 0.5) / TW * 2 - 1)
        t = (vv + 0.5) / hh
        # (the sides fade out, more toward the root, where the strip cuts across its neighbours; the root's corners
        # rounded off)
        alpha *= sstep_np(1.0, side, s)
        alpha *= sstep_np(1.0, 0.75, s + 0.35 * np.clip(0.2 - t, 0, None) / 0.2)
        # (and narrow toward the tip, as a lock does, so a card's sides never show as straight edges)
        alpha *= sstep_np(1.0, 0.85, s + taper * t ** 1.5)
    if not solid:
        # (the edge pixels are part ground: give every pixel short of full hair the colour of the hair near it, so a
        # cut edge has no pale halo)
        core = (KEYS[key](rgb) > 0.95).astype(float)
        near = blur(rgb * core[..., None], 3) / np.maximum(blur(core, 3), 1e-3)[..., None]
        far = blur(rgb * core[..., None], 12) / np.maximum(blur(core, 12), 1e-3)[..., None]
        fill = np.where((blur(core, 3) > 0.02)[..., None], near, far)
        rgb = np.where((core > 0.5)[..., None], rgb, fill)
    # (take the painting's broad light out: divide by its large blur, weighted to the hair, put back a flat tone)
    L = lum(rgb)
    wgt = np.clip(alpha, 0.05, 1.0)
    big = blur(L * wgt, 18) / np.maximum(blur(wgt, 18), 1e-3)
    k = (lift_to / np.maximum(big, 0.05)) ** flat * gain
    rgb = np.clip(rgb * k[..., None] * np.array(warm), 0.0, 1.0)
    # (the outermost pixels clear, so mipmaps do not bleed one tile into the next)
    if not solid:
        alpha[:, :2] = 0
        alpha[:, -2:] = 0
        alpha[-2:, :] = 0
    img[y0 + r0:y0 + r1, x0:x0 + TW, :3] = rgb
    img[y0 + r0:y0 + r1, x0:x0 + TW, 3] = np.clip(alpha, 0, 1)


def palette_from(src, box, key, darken=1.0, saturate=1.0, lit=0.0, tint=(1.0, 1.0, 1.0)):
    """The five colours of paint_lock's palette (darkest to lightest) read from the hair in a box of a concept sheet
    (x0, y0, x1, y1 in its pixels): the mean colour of the hair at five bands of lightness. lit (0..1) moves the bands
    toward the sheet's lit hair (its shadows can be greener than its hair: the boy's read olive), tint multiplies."""
    x0, y0, x1, y1 = box
    c = sheet(src)[y0:y1, x0:x1].reshape(-1, 3)
    c = c[KEYS[key](c) > 0.9]
    c = c[np.argsort(lum(c))]
    n = len(c)
    out = []
    for lo, hi in ((0.0, 0.08), (0.25, 0.4), (0.55, 0.7), (0.85, 0.93), (0.97, 1.0)):
        lo, hi = lo + (1 - lo) * lit * 0.5, hi + (1 - hi) * lit * 0.5
        m = c[int(lo * n):max(int(hi * n), int(lo * n) + 1)].mean(axis=0)
        m = lum(m) + (m - lum(m)) * saturate
        out.append(tuple(min(float(min(max(x, 0.0), 1.0)) * darken * k, 1.0) for x, k in zip(m, tint)))
    return out


def save_image(img, name, path):
    im = bpy.data.images.new(name, ATLAS, ATLAS, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(img[::-1]).ravel().astype(np.float32))
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    return im


def tile_uv(tile, s, t):
    """UV (Blender's, v up) of a point across s 0..1 and along t 0..1 of a tile."""
    col, row = tile % 4, tile // 4
    mu, mv = 1.5 / ATLAS, 2.5 / ATLAS
    u = (col + mu * 4 + s * (1 - 8 * mu)) / 4
    v_top = 1.0 - row * 0.5 - mv
    return (u, v_top - t * (0.5 - 2 * mv))


# ---------------------------------------------------------------------------------------------------------------------
# A mass of hair: under-shell and card layers


class Builder:
    def __init__(self, head, mass, rng):
        self.h, self.m, self.rng = head, mass, rng
        self.verts, self.faces = [], []

    def thick(self, d):
        a, e = angles(d)
        return self.m["thick"](a, e) * self.h.size

    def hull(self, d, extra=1.0):
        return self.h.c + d.normalized() * (self.h.skin(d) + self.thick(d) * extra)

    def hull_normal(self, d):
        d = d.normalized()
        t1 = d.cross(Vector((0, 0, 1)))
        if t1.length < 0.1:
            t1 = d.cross(Vector((1, 0, 0)))
        t1.normalize()
        t2 = d.cross(t1).normalized()
        k = 0.06
        p0 = self.hull(d)
        n = (self.hull(d + t1 * k) - p0).cross(self.hull(d + t2 * k) - p0)
        if n.dot(d) < 0:
            n = -n
        return n.normalized()

    def add(self, pts, uvs, cols, nors):
        """One face (3 or 4 corners) with its own UVs, colours and normals; wound so it faces like its normals."""
        if len(pts) == 4:
            # (two triangles, each wound by its own normals: a bent quad's halves can face apart)
            self.add(pts[:3], uvs[:3], cols[:3], nors[:3])
            self.add([pts[0], pts[2], pts[3]], [uvs[0], uvs[2], uvs[3]], [cols[0], cols[2], cols[3]],
                     [nors[0], nors[2], nors[3]])
            return
        cap = getattr(self, "cap", None)
        if cap is not None:
            # (under a cap: nothing may come through it; a point the cap lies between the head's middle and is
            # pulled back inside it, 4 mm under its inner side)
            out = []
            for p in pts:
                d = p - self.h.c
                hit = cap.ray_cast(self.h.c, d.normalized(), d.length + 0.004)
                # (but never under the skin: with the cap off, what was under it shows as a thin layer)
                out.append(self.h.c + d.normalized() * max((hit[0] - self.h.c).length - 0.004, self.h.skin(d) + 0.0015)
                           if hit[0] is not None else p)
            pts = out
        a, b, c = pts[:3]
        if (b - a).cross(c - a).dot(sum(nors, Vector())) < 0:
            pts, uvs, cols, nors = pts[::-1], uvs[::-1], cols[::-1], nors[::-1]
        self.faces.append((pts, uvs, cols, nors))

    def inside(self, a, e):
        m = self.m
        return (m["low"](a) < e < m.get("high", lambda _a: 91.0)(a) and m.get("gap", -1.0) <= abs(a)
                <= m.get("reach", 180.0))

    def shell(self):
        m = self.m
        cols = m["shell_cols"]
        rows = m["shell_rows"]
        reach = m.get("reach", 180.0)
        full = reach >= 180.0
        span = 360.0 if full else 2 * reach
        for j in range(cols):
            a0 = -span / 2 + span * j / cols
            a1 = -span / 2 + span * (j + 1) / cols
            if min(abs(a0), abs(a1)) < m.get("gap", -1.0) - 0.01 or (a0 < 0 < a1 and m.get("gap", -1.0) > 0):
                continue
            ring = []
            for a in (a0, a1):
                hi = min(m.get("high", lambda _a: 91.0)(a), m.get("shell_top", 86.0))
                sp = m.get("shell_past", 3.0)
                lo = m["low"](a) - (sp(a) if callable(sp) else sp)
                col = []
                band = m.get("shell_band", 8.0)
                tb = m.get("top_band", False)
                for r in range(rows + 1):
                    t = r / rows
                    # (the last row is a narrow band of pointed strands, the rest share the way up evenly; with
                    # top_band the first row is one too, its strands pointing up: a beard's cheek line)
                    first = 1 if tb else 0
                    x = (r - first) / max(rows - 1 - first, 1)
                    e = lo if r == rows else (hi if (tb and r == 0) else lerp(hi - (band if tb else 0), lo + band, x))
                    d = direction(a, e)
                    # (full thickness inside, down to the skin at the last row, which is the band of strands)
                    f = 0.0 if (r == rows or (tb and r == 0)) else m["shell_frac"] * (1.0 - 0.6 * x ** 2)
                    p = self.h.c + d * (max(self.h.skin(d), self.h.skin_raw(d) if m.get("over_raw") else 0)
                                        + self.thick(d) * f + 0.003)
                    col.append((p, self.hull_normal(d), t))
                ring.append(col)
            for r in range(rows):
                last = r == rows - 1
                # (each quad of the mass takes a square quarter of the tile's top half, picked at random, so the
                # painting is not stretched down a row; the last row takes the whole band of tufts)
                if last:
                    t0, t1, s0, s1 = 0.5, 1.0, 0.0, 1.0
                elif r == 0 and m.get("top_band", False):
                    t0, t1, s0, s1 = 1.0, 0.5, 0.0, 1.0
                else:
                    t0 = self.rng.choice((0.0, 0.25))
                    s0 = self.rng.choice((0.0, 0.5))
                    t1, s1 = t0 + 0.25, s0 + 0.5
                (p00, n00, _), (p01, n01, _) = ring[0][r], ring[0][r + 1]
                (p10, n10, _), (p11, n11, _) = ring[1][r], ring[1][r + 1]
                st = m.get("shell_tile", 0)
                uvs = [tile_uv(st, s0, t0), tile_uv(st, s0, t1), tile_uv(st, s1, t1), tile_uv(st, s1, t0)]
                shade = m.get("shell_shade", 0.45)
                g0, g1 = 0.5 + 0.5 * r / rows, 0.5 + 0.5 * (r + 1) / rows
                # (shade_at darkens the shell too: the soft shadow under a moustache)
                sa = m.get("shade_at", lambda _a, _e: 1.0)
                sh = [shade * sa(*angles(q - self.h.c)) for q in (p00, p01, p11, p10)]
                cl = [(sh[0], g0, 0, 1), (sh[1], g1, 0, 1), (sh[2], g1, 0, 1), (sh[3], g0, 0, 1)]
                self.add([p00, p01, p11, p10], uvs, cl, [n00, n01, n11, n10])
            # (a fan to the top, when the shell reaches it)
            hi0 = min(m.get("high", lambda _a: 91.0)(a0), m.get("shell_top", 86.0))
            if hi0 >= m.get("shell_top", 86.0) - 0.1:
                dtop = direction(0, 90)
                ptop = self.h.c + dtop * (self.h.skin(dtop) + self.thick(dtop) * m["shell_frac"] + 0.002)
                ntop = self.hull_normal(dtop)
                (p00, n00, _), (p10, n10, _) = ring[0][0], ring[1][0]
                st = m.get("shell_tile", 0)
                uvs = [tile_uv(st, 0.5, 0.0), tile_uv(st, 0, 0.05), tile_uv(st, 1, 0.05)]
                shade = m.get("shell_shade", 0.45)
                self.add([ptop, p00, p10], uvs, [(shade, 0.2, 0, 1)] * 3, [ntop, n00, n10])

    def seeds(self, count, band, min_deg, tries=6000, arc=180.0):
        out = []
        lo_e, hi_e = band
        for _ in range(tries):
            if len(out) >= count:
                break
            z = self.rng.uniform(-1, 1)
            a = self.rng.uniform(-180, 180)
            e = math.degrees(math.asin(z))
            if not self.inside(a, e) or abs(a) > arc:
                continue
            # (band: share of the way from the hairline (0) up to the top or the high edge (1))
            lo = self.m["low"](a)
            hi = min(self.m.get("high", lambda _a: 90.0)(a), 90.0)
            share = (e - lo) / max(hi - lo, 1e-3)
            if not (lo_e <= share <= hi_e):
                continue
            d = direction(a, e)
            if any(d.angle(o) < math.radians(min_deg) for o in out):
                continue
            out.append(d)
        return out

    def card(self, d0, layer):
        m, rng = self.m, self.rng
        length = rng.uniform(*layer["length"]) * self.h.size
        width = rng.uniform(*layer["width"]) * self.h.size
        rows = layer.get("rows", 3)
        # (march along the comb on the hull in fine steps, stopping at the limit the hair may fall to)
        fine = 16
        pts = [d0.normalized()]
        for k in range(fine):
            d = pts[-1]
            a, e = angles(d)
            g = layer.get("comb", m["comb"])(a, e, d)
            g = (g - d * g.dot(d))
            if g.length < 1e-6:
                break
            g.normalize()
            r = self.h.skin(d) + self.thick(d)
            nd = (d + g * (length / fine) / r).normalized()
            na, ne = angles(nd)
            if ne < m["fall"](na):
                break
            pts.append(nd)
        if len(pts) < 4:
            return
        # (resample to rows + 1 along)
        cum = [0.0]
        for p, q in zip(pts, pts[1:]):
            cum.append(cum[-1] + p.angle(q))
        dirs = []
        for r in range(rows + 1):
            target = cum[-1] * r / rows
            k = max(i for i in range(len(cum)) if cum[i] <= target + 1e-9)
            k = min(k, len(pts) - 2)
            f = (target - cum[k]) / max(cum[k + 1] - cum[k], 1e-9)
            dirs.append(pts[k].lerp(pts[k + 1], min(f, 1.0)).normalized())
        real = cum[-1] / cum[-1] if cum[-1] > 0 else 1
        tile = rng.choice(layer["tiles"])
        flip = rng.random() < 0.5
        lift = rng.uniform(*layer.get("lift", (0.0, 0.0))) * self.h.size
        r0, r1 = layer["depth"]
        shade = layer["shade"] * self.m.get("shade_at", lambda _a, _e: 1.0)(*angles(d0))
        spin = rng.uniform(-1, 1) * layer.get("spin", 0.0)
        # (first the lock's frame row by row along the hull: where, its hull normal, along and across)
        frames = []
        for r, d in enumerate(dirs):
            t = r / rows
            base = max(self.h.skin(d), self.h.skin_raw(d) if m.get("over_raw") else 0.0)
            rad = base + self.thick(d) * lerp(r0, r1, sstep(0.0, 0.7, t)) + lift * t * t + 0.003
            p = self.h.c + d * rad
            n = self.hull_normal(d)
            nxt = dirs[min(r + 1, rows)] if r < rows else d
            prv = dirs[max(r - 1, 0)]
            along = (self.h.c + nxt * rad) - (self.h.c + prv * rad)
            if along.length < 1e-6:
                along = n.cross(Vector((1, 0, 0)))
            along.normalize()
            across = n.cross(along).normalized()
            # (a small twist about the lock, so neighbouring cards are not all flat to the hull)
            across = (across + n * spin * t).normalized()
            if layer.get("fin"):
                # (a FIN: the card stands up from the mass instead of lying on it, half inside, half out, so its
                # painted curl is seen whole wherever the lock is on the outline (shells and fins, as fur is drawn
                # in games); seen face on it is edge on, and the mass behind covers it)
                across = (n + across * spin).normalized()
            frames.append([p, n, along, across])
        # (a HOOK: past hook_from the lock rolls over in a C, its end turning out from the head (or, sign -1, under
        # it): a curl in the lock itself, so the outline breaks into curls, not flat flaps)
        hook = rng.uniform(*layer.get("hook", (0.0, 0.0)))
        if hook > 0.0:
            k0 = next((r for r in range(rows + 1) if r / rows >= layer.get("hook_from", 0.5)), rows)
            sign = 1.0 if rng.random() < layer.get("hook_out", 0.8) else -1.0
            p0, n0, a0, c0 = frames[k0]
            segs = [(frames[r + 1][0] - frames[r][0]).length for r in range(k0, rows)]
            total = max(sum(segs), 1e-6)
            P, phi = p0.copy(), 0.0
            for i, r in enumerate(range(k0 + 1, rows + 1)):
                mid = phi + hook * segs[i] / total * 0.5
                P = P + (a0 * math.cos(mid) + n0 * sign * math.sin(mid)) * segs[i]
                phi += hook * segs[i] / total
                frames[r][0] = P.copy()
                frames[r][1] = (n0 * math.cos(phi) - a0 * sign * math.sin(phi)).normalized()
                frames[r][2] = (a0 * math.cos(phi) + n0 * sign * math.sin(phi)).normalized()
                frames[r][3] = c0
        clump = layer.get("clump", 0.0)
        rowsets = []
        for r, (p, n, along, across) in enumerate(frames):
            t = r / rows
            w = width * (1.0 - 0.25 * t)
            cup = layer.get("cup", 0.18) * w
            row = []
            for s in (0.0, 0.5, 1.0):
                off = (s - 0.5) * w
                q = p + across * off - n * cup * (2 * s - 1) ** 2
                # (never under the skin)
                dd = (q - self.h.c)
                if dd.length < self.h.skin(dd) + 0.002:
                    q = self.h.c + dd.normalized() * (self.h.skin(dd) + 0.002)
                # (the normal: the hull's (one soft mass) leaned toward the lock's own, rounded across it (clump), so
                # each lock has its own lit side and shadow side within the mass)
                nn = self.hull_normal(q - self.h.c).lerp(n, 0.5).normalized()
                nn = (nn + across * (2 * s - 1) * clump).normalized()
                su = (1 - s) if flip else s
                row.append((q, tile_uv(tile, su, t), (shade, t, 1, 1), nn))
            rowsets.append(row)
        for r in range(rows):
            for c in range(2):
                corners = [rowsets[r][c], rowsets[r + 1][c], rowsets[r + 1][c + 1], rowsets[r][c + 1]]
                self.add([x[0] for x in corners], [x[1] for x in corners], [x[2] for x in corners],
                         [x[3] for x in corners])

    def lock(self, k):
        """One MODELLED LOCK (a chunky curl): a fat ribbon with a raised crest, a triangle in section (two lit sides
        meeting at the crest, a flat belly under it), combed along the hull from its root, then rolled over in a C at
        its end (curl, radians; + out from the head) while it bends sideways (swing, radians over its length, for an
        S across the head), ending in a rounded cap. k: a (azimuth), e (elevation) of the root; comb (a function of
        the direction, the way to go along the head); length, width (head sizes); curl, curl_from (the share of the
        length where the roll starts); swing; depth (root, body: shares of the mass's thickness); shade.
        Since the fourth pass the section is a soft arch (see the comment in the body; keys across, round, hull,
        taper, tip, crest, edge): 6 rows x 3 quads + a cap of 3 = 39 triangles (33 with 5 rows)."""
        h, m = self.h, self.m
        size = h.size
        length, width = k["length"] * size, k["width"] * size
        rows = k.get("rows", 5)
        d0 = direction(k["a"], k["e"])
        fine = 20
        pts = [d0]
        swing = k.get("swing", 0.0)
        for i in range(fine):
            d = pts[-1]
            g = k["comb"](d)
            g = g - d * g.dot(d)
            if g.length < 1e-6:
                break
            g.normalize()
            # (bend sideways as it goes: the comb turned about the head's normal)
            th = swing * (i + 0.5) / fine
            g = (g * math.cos(th) + d.cross(g) * math.sin(th)).normalized()
            r = h.skin(d) + self.thick(d)
            nd = (d + g * (length / fine) / r).normalized()
            na, ne = angles(nd)
            if ne < m["fall"](na):
                break
            pts.append(nd)
        if len(pts) < 4:
            return
        cum = [0.0]
        for p, q in zip(pts, pts[1:]):
            cum.append(cum[-1] + p.angle(q))
        dirs = []
        for r in range(rows + 1):
            target = cum[-1] * r / rows
            i = min(max(j for j in range(len(cum)) if cum[j] <= target + 1e-9), len(pts) - 2)
            f = (target - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
            dirs.append(pts[i].lerp(pts[i + 1], min(f, 1.0)).normalized())
        dr0, dr1 = k.get("depth", (0.45, 0.85))
        lift = k.get("lift", 0.0) * size
        frames = []
        for r, d in enumerate(dirs):
            t = r / rows
            rad = h.skin(d) + self.thick(d) * lerp(dr0, dr1, sstep(0.0, 0.6, t)) + lift * t * t
            p = h.c + d * rad
            n = self.hull_normal(d)
            nxt, prv = dirs[min(r + 1, rows)], dirs[max(r - 1, 0)]
            along = (h.c + nxt * rad) - (h.c + prv * rad)
            if along.length < 1e-6:
                along = n.cross(Vector((1, 0, 0)))
            along = (along - n * along.dot(n)).normalized()
            frames.append([p, n, along, n.cross(along).normalized()])
        # (the roll: from curl_from on, the lock turns over in the plane of its length and the head's normal)
        curl = k.get("curl", 0.0)
        if abs(curl) > 1e-3:
            k0 = next((r for r in range(rows + 1) if r / rows >= k.get("curl_from", 0.5)), rows)
            p0, n0, a0, c0 = frames[k0]
            sign = 1.0 if curl > 0 else -1.0
            segs = [(frames[r + 1][0] - frames[r][0]).length for r in range(k0, rows)]
            total = max(sum(segs), 1e-6)
            P, phi = p0.copy(), 0.0
            for i, r in enumerate(range(k0 + 1, rows + 1)):
                step = abs(curl) * segs[i] / total
                mid = phi + step * 0.5
                P = P + (a0 * math.cos(mid) + n0 * sign * math.sin(mid)) * segs[i]
                phi += step
                frames[r][0] = P.copy()
                frames[r][1] = (n0 * math.cos(phi) - a0 * sign * math.sin(phi)).normalized()
                frames[r][2] = (a0 * math.cos(phi) + n0 * sign * math.sin(phi)).normalized()
        shade = k.get("shade", 1.0)
        tile = k.get("tile", 1)
        # FOURTH PASS (2026-11-18): the lock is a SOFT ARCH, not a crested prism. The third pass's triangular section lit
        # as two flat planes meeting at a hard crest and read as wood chips. Now: an arch of `across` points (4 by
        # default: s -1, -1/3, 1/3, 1), thick in the middle, its edges tucked down into the mass under it, so it has
        # no edge to show and no belly to draw (the shader draws both sides with the outward normal); the normal at
        # every point is the arch's own (turning across it, and along it with the curl) blended `hull` (0.6) toward
        # the smooth hull's, so the whole mop lights as one soft mass with the locks as a secondary rhythm; the crest
        # is the shader's soft highlight (`crest_gain`, from the tile's u), not a ridge; the width tapers to a
        # rounded point that rolls over with the curl.
        hull_k = k.get("hull", 0.6)
        ns = k.get("across", 4)
        ss = [-1.0 + 2.0 * i / (ns - 1) for i in range(ns)]
        taper = k.get("taper", [(0.0, 0.72), (0.18, 1.0), (0.6, 0.9), (0.85, 0.62), (1.0, 0.34)])
        rings = []
        for r, (p, n, along, across) in enumerate(frames):
            t = r / rows
            w = width * pw(taper, t)
            ht = w * k.get("crest", 0.3) * pw([(0.0, 0.55), (0.3, 1.0), (1.0, 0.8)], t)
            hn = self.hull_normal(p - h.c)
            pts, nors = [], []
            for s in ss:
                # (a soft arch: up by cos across, the edges dipped under the root line)
                lift_s = ht * (math.cos(s * math.pi / 2) ** 0.8) - ht * 0.35 * s * s
                q = p + across * (s * w * 0.5) + n * lift_s
                dd = q - h.c
                if dd.length < h.skin(dd) + 0.002:
                    q = h.c + dd.normalized() * (h.skin(dd) + 0.002)
                th = s * math.radians(k.get("round", 62.0))
                own = (n * math.cos(th) + across * math.sin(th)).normalized()
                pts.append(q)
                nors.append(own.lerp(hn, hull_k).normalized())
            rings.append((pts, nors, t, along, n))
        edge = k.get("edge", 0.86)
        for r in range(rows):
            (q0, n0, t0, _, _), (q1, n1, t1, _, _) = rings[r], rings[r + 1]
            for i in range(ns - 1):
                j = i + 1
                si, sj = (ss[i] + 1) / 2, (ss[j] + 1) / 2
                ci = shade * lerp(edge, 1.0, 1.0 - ss[i] ** 2)
                cj = shade * lerp(edge, 1.0, 1.0 - ss[j] ** 2)
                self.add([q0[i], q1[i], q1[j], q0[j]],
                         [tile_uv(tile, si, t0), tile_uv(tile, si, t1), tile_uv(tile, sj, t1), tile_uv(tile, sj, t0)],
                         [(ci, t0, 1, 1), (ci, t1, 1, 1), (cj, t1, 1, 1), (cj, t0, 1, 1)],
                         [n0[i], n1[i], n1[j], n0[j]])
        # (a rounded end: the last ring's points meet a point a little past it, its normal the end's own, softened)
        q, nn, t, along, n = rings[-1]
        w = (q[-1] - q[0]).length
        mid = sum(q, Vector()) / len(q)
        tip = mid + along * w * k.get("tip", 0.55) - n * w * 0.08
        nt = (along * 0.5 + n).normalized().lerp(self.hull_normal(tip - h.c), hull_k).normalized()
        for i in range(ns - 1):
            j = i + 1
            ci = shade * lerp(edge, 1.0, 1.0 - ss[i] ** 2)
            cj = shade * lerp(edge, 1.0, 1.0 - ss[j] ** 2)
            self.add([q[i], q[j], tip], [tile_uv(tile, (ss[i] + 1) / 2, 0.97), tile_uv(tile, (ss[j] + 1) / 2, 0.97),
                                         tile_uv(tile, 0.5, 1.0)], [(ci, 1, 1, 1), (cj, 1, 1, 1), (shade, 1, 1, 1)],
                     [nn[i], nn[j], nt])

    def build(self):
        if self.m.get("shell_cols"):
            self.shell()
        print("HAIR shell faces", len(self.faces))
        if "locks" in self.m:
            specs = self.m["locks"](self.rng)
            for k in specs:
                self.lock(k)
            print("HAIR locks", len(specs))
        for layer in self.m.get("layers", []):
            for d in self.seeds(layer["count"], layer["band"], layer["spacing"], arc=layer.get("arc", 180.0)):
                self.card(d, layer)

    def to_object(self, name, mat):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        col = bm.loops.layers.color.new("Color")
        normals = []
        for pts, uvs, cols, nors in self.faces:
            vs = [bm.verts.new(p) for p in pts]
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            for lp, u, c, n in zip(f.loops, uvs, cols, nors):
                lp[uv].uv = u
                lp[col] = c
                normals.append(n)
        bm.to_mesh(me)
        bm.free()
        me.normals_split_custom_set([tuple(n) for n in normals])
        me.color_attributes.active_color_index = 0
        me.color_attributes.render_color_index = 0
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if "jaw" in self.m:
            # (what each point follows, for the face rig: see JAW in the module's docstring)
            w = [min(max(float(self.m["jaw"](*angles(v.co - self.h.c))), 0.0), 1.0) for v in me.vertices]
            att = me.attributes.new("_JAW", "FLOAT", "POINT")
            att.data.foreach_set("value", w)
            gj, gh = ob.vertex_groups.new(name="follow_jaw"), ob.vertex_groups.new(name="follow_head")
            for i, x in enumerate(w):
                if x > 1e-4:
                    gj.add([i], x, "REPLACE")
                if x < 1.0 - 1e-4:
                    gh.add([i], 1.0 - x, "REPLACE")
        return ob


# ---------------------------------------------------------------------------------------------------------------------
# The figures


def comb_from(crown, fall, forward=0.0):
    """Hair combed out from a crown (a direction in the head frame) and falling with gravity."""
    cr = crown.normalized()

    def comb(a, e, d):
        away = d - cr
        if away.length < 1e-3:
            away = Vector((0, -1, 0))
        return away.normalized() + Vector((0, 0, -fall)) + Vector((0, -forward, 0))
    return comb


def brother():
    # Thick tousled mop of curls, shorter at the sides, falling on the forehead (the user); concept_brother_head3.jpg
    # (the settled sheet, top row): the curls stand 4 to 6 cm off the skull all round, wider than the head at the
    # temples, tall on top, a tousled fringe on the forehead, a ragged outline of fat curled locks.
    # (fourth pass: dark brown overall, fixed: the colours read from the sheet came out orange; the amber-red is the
    # shader's sheen only, "dark hair but amberish red in the right light")
    pal = [(0.1, 0.064, 0.042), (0.21, 0.13, 0.08), (0.34, 0.215, 0.125), (0.48, 0.31, 0.175), (0.63, 0.42, 0.25)]
    # THIRD PASS (2026-11-18): MODELLED LOCKS. Cards and fins (the first two passes) read as a nest of small flakes in
    # a tight cap; the sheet's mop is a big soft mass of 25 to 40 large readable curls. So the mop is now chunky
    # modelled locks (Builder.lock: fat crested ribbons 3 to 6 cm wide, about 33 triangles each, rolled over in a C at
    # their ends, bent sideways for an S), over the dark under-shell, shaded smooth by the hair shader with each lock's
    # crest light and its belly and edges dark (vertex colour). The usual way for stylised hair in games (Twilight
    # Princess, Wind Waker, Genshin): solid opaque chunks for the big clumps, edge loops along the flow, smooth normals.
    crown = direction(180, 60)
    down = Vector((0, 0, -1))
    low = lambda a: 3.0 * math.sin(a * 0.37) + pw([(0, 25), (25, 24), (45, 15), (60, 4), (75, -5), (100, -7),
                                                   (108, -3), (128, -3), (138, -12), (150, -24), (180, -30)], abs(a))

    def at(a, share):
        lo = low(a)
        return lo + (88.0 - lo) * share

    def away(fall):
        # (out from the crown's whorl, falling with gravity)
        def f(d):
            g = d - crown
            if g.length < 1e-3:
                g = Vector((0, -1, 0))
            return g.normalized() + down * fall
        return f

    def toward(target):
        tg = target.normalized()
        return lambda d: (tg - d)

    def locks(rng):
        # FOURTH PASS: combed, not jumbled. Every lock in a region shares its comb and its sideways bend (swing), with
        # only 4 degrees of jitter at the root and about 10 degrees in the bend, so neighbours lie nearly parallel and
        # shingle from the crown outward like roof tiles; all roll over in a C at their ends (rounded points), so the
        # outline is a row of curl ends.
        out = []

        def add(a, share, comb, length, width, curl, curl_from=0.5, swing=0.0, depth=(0.55, 0.85), shade=1.0,
                lift=0.0, rows=6):
            a = a + rng.uniform(-4, 4)
            s = min(max(share + rng.uniform(-0.06, 0.06), 0.0), 0.98)
            out.append(dict(a=a, e=at(a, s), comb=comb, length=length * rng.uniform(0.82, 1.18),
                            width=width * rng.uniform(0.9, 1.1), curl=curl * rng.uniform(0.75, 1.25),
                            curl_from=curl_from, swing=swing + rng.uniform(-0.17, 0.17), depth=depth,
                            shade=shade * rng.uniform(0.95, 1.03), lift=lift, rows=rows, crest=0.34, edge=0.82,
                            hull=0.6, tile=rng.choice((1, 2)), tip=0.32,
                            taper=[(0.0, 0.9), (0.2, 1.0), (0.6, 0.92), (0.85, 0.7), (1.0, 0.48)]))

        # Curls on the top, the crown and the back roll UNDER (curl < 0): the bend of each C is what shows, so the
        # outline is a row of rounded curl backs, not points; the nape and the sides over the ears roll OUT.
        # the nape: falling to the neck's top, the ends rolled up and out (a full curly nape)
        for a in (180, 160, -160, 140, -140, 120, -120):
            add(a, 0.06, away(0.8), 0.2, 0.3, 1.0, 0.45, 0.2 * math.copysign(1, a) if a != 180 else 0.0,
                (0.5, 0.75), 0.92, rows=5)
        # the back, two rows, shingled over the nape's roots
        for a in (180, 158, -158, 136, -136, 114, -114):
            add(a, 0.3, away(0.5), 0.4, 0.27, -1.5, 0.45, 0.2 * math.copysign(1, a) if a != 180 else 0.0,
                (0.65, 0.92), 0.94)
        for a in (169, -169, 146, -146, 123, -123):
            add(a, 0.56, away(0.35), 0.4, 0.27, -1.4, 0.45, 0.15 * math.copysign(1, a), (0.72, 0.95), 0.97, rows=5)
        # the crown: the whorl, short locks lying close
        for a in (180, 135, -135, 90, -90):
            add(a, 0.88, away(0.1), 0.32, 0.26, -1.2, 0.45, 0.6, (0.8, 0.95), 1.0, rows=5)
        # the sides, shorter (the user): down and a little back to the ears' tops, curling out
        for sg in (1, -1):
            add(sg * 96, 0.3, away(0.7), 0.22, 0.27, -1.2, 0.4, sg * 0.3, (0.6, 0.8), 0.92, rows=5)
            add(sg * 72, 0.3, away(0.65), 0.22, 0.27, -1.2, 0.4, sg * 0.3, (0.6, 0.8), 0.92, rows=5)
            add(sg * 88, 0.5, away(0.45), 0.36, 0.27, -1.4, 0.45, sg * 0.2, (0.7, 0.92), 0.96)
            add(sg * 62, 0.5, away(0.4), 0.36, 0.27, -1.4, 0.45, sg * 0.2, (0.7, 0.92), 0.96)
        # the upper ring, from the crown outward
        for a in (106, -106, 74, -74, 42, -42):
            add(a, 0.74, away(0.25), 0.38, 0.28, -1.3, 0.45, 0.2 * math.copysign(1, a), (0.8, 0.97), 0.99)
        # the top: swept up and back off the forehead, rolling under at the crown
        for a in (-36, -12, 12, 36):
            add(a, 0.04, toward(crown), 0.42, 0.28, -1.1, 0.5, 0.2, (0.66, 0.95), 1.0)
        # the fringe: from behind the hairline falling forward onto the forehead, all swept to one side (the
        # figure's left, as the sheet's front view), the ends curling under
        side = lambda d: Vector((0.55, -1, -0.65))
        for a, ln in ((-24, 0.34), (4, 0.42), (22, 0.58)):
            add(a, 0.36, side, ln, 0.28, -1.8, 0.6, 0.25, (0.95, 1.06), 1.03)
        for sg in (1, -1):
            add(sg * 52, 0.26, lambda d, sg=sg: Vector((sg * 0.6, -1, -0.65)), 0.34, 0.26, -1.5, 0.5, sg * 0.2,
                (0.85, 1.0), 1.0)
        return out

    hair = dict(
        low=low,
        # (how far down a lock may fall: the fringe to the brows' top, the nape to the neck's top)
        fall=lambda a: 4.0 * math.sin(a * 0.21) + 2.5 * math.sin(a * 0.53 + 1.0)
        + pw([(0, -2), (12, -7), (24, -4), (36, 4), (45, 5), (60, -6), (75, -12), (100, -13), (108, -8), (128, -8), (138, -18),
              (150, -32), (180, -40)], abs(a)),
        # (the mop's thickness off the skull, head sizes (0.2 m): about 3 cm at the sides, 5 to 6 cm on top; the
        # locks' crests stand a centimetre or two over it)
        # (fourth pass: a broad rounded top, not a peak: the top no thicker than the temples, the temples fuller)
        thick=lambda a, e: lerp(pw([(0, 0.2), (55, 0.3), (100, 0.3), (130, 0.26), (180, 0.22)], abs(a)), 0.25,
                                sstep(30, 80, e)) * (0.6 + 0.4 * sstep(-40, 10, e)),
        comb=away(0.25),
        # (the under-shell a warm dark brown near the locks' own shade, so no black holes between them; it stops
        # short of the hairline (the locks hang past it), so its edge never shows as a jagged band from below)
        shell_cols=18, shell_rows=5, shell_frac=0.8, shell_shade=0.92,
        shell_past=lambda a: pw([(0, -9), (40, -8), (90, -3), (125, 2), (150, 7), (180, 8)], abs(a)),
        locks=locks,
    )
    tiles = [
        # (the under-shell: a soft surface, low in contrast (strands striped it); it ends above the hairline, so it
        # needs no band of tips)
        dict(surface=dict(grooves=4.0, lo=0.4, hi=0.5, streak=0.03)),
        dict(surface=dict(grooves=3.0, lo=0.42, hi=0.62, streak=0.04)),
        dict(surface=dict(grooves=2.0, lo=0.42, hi=0.6, streak=0.04)),
        # (the moustache: lighter and softer than the mop, as the sheet paints it)
        dict(surface=dict(grooves=6.0, lo=0.56, hi=0.66, streak=0.03)),
    ]
    # A thin young man's moustache (the user's settled sheet): a thin soft dark-brown shell on the upper lip, no cards
    # (the cards read as a bristly orange strip); the stubble is left to the face paint. It follows the upper lip
    # (the head), not the jaw: see JAW in the module's docstring.
    moustache = dict(
        centre=(0.09, -0.32),
        high=lambda a: pw([(0, -4.5), (12, -5.5), (20, -8.5)], abs(a)),
        low=lambda a: pw([(0, -7.5), (12, -8.5), (20, -11.5)], abs(a)),
        reach=20, shell_tile=3,
        fall=lambda a: pw([(0, -11), (24, -19)], abs(a)),
        thick=lambda a, e: 0.022 * (1.0 - 0.5 * sstep(10, 22, abs(a))),
        comb=lambda a, e, d: Vector((math.copysign(1.0, a) if abs(a) > 2 else 0.0, -0.1, -0.7)),
        shell_cols=8, shell_rows=2, shell_frac=0.9, shell_shade=1.0, top_band=False, shell_band=2.0,
        shell_past=0.0, shell_top=90.0, jaw=lambda a, e: 0.0,
    )
    return pal, tiles, {"hair": hair, "moustache": moustache}


def boy():
    # A fresh blond tousled mop (the user); concept_boy_head2.jpg: a fringe to the brows, the ears out, the nape
    # covered, straight locks breaking into pointed tips all round.
    pal = [(0.44, 0.34, 0.18), (0.66, 0.53, 0.31), (0.81, 0.68, 0.42), (0.91, 0.81, 0.56), (0.98, 0.93, 0.72)]
    hair = dict(
        low=lambda a: pw([(0, 30), (30, 28), (55, 14), (75, 2), (98, -2), (106, 8), (128, 6), (140, -18),
                          (160, -40), (180, -47)], abs(a)),
        fall=lambda a: 3.0 * math.sin(a * 0.23) + pw([(0, 15), (30, 12), (55, 2), (75, -8), (98, -6), (106, 4),
                                                       (128, 2), (140, -24), (160, -48), (180, -56)], abs(a)),
        thick=lambda a, e: lerp(pw([(0, 0.18), (50, 0.27), (75, 0.27), (100, 0.2), (130, 0.24), (180, 0.22)], abs(a)), 0.34,
                                sstep(15, 70, e)) * (0.4 + 0.6 * sstep(-35, 20, e)),
        comb=comb_from(direction(180, 58), 0.35, 0.0),
        shell_cols=20, shell_rows=5, shell_frac=0.85, shell_shade=0.85,
        layers=[
            dict(count=26, band=(0.0, 0.75), spacing=21, length=(0.5, 0.65), width=(0.4, 0.5), tiles=[1, 2, 3],
                 depth=(0.5, 0.95), lift=(0.0, 0.05), shade=0.82, spin=0.2),
            dict(count=13, band=(0.0, 0.22), arc=75, spacing=12, length=(0.45, 0.62), width=(0.34, 0.44),
                 tiles=[4, 5, 6], depth=(0.5, 0.35), lift=(0.0, 0.03), shade=0.92, spin=0.15),
            dict(count=26, band=(0.15, 1.0), spacing=19, length=(0.45, 0.6), width=(0.38, 0.48), tiles=[1, 2, 4, 5],
                 depth=(0.7, 1.05), lift=(0.02, 0.08), shade=0.94, spin=0.3),
            dict(count=28, rows=2, band=(0.2, 1.0), spacing=16, length=(0.32, 0.44), width=(0.3, 0.4),
                 tiles=[5, 6, 7], depth=(0.8, 1.12), lift=(0.02, 0.07), shade=1.0, spin=0.4),
        ],
    )
    # (the colours are the boy's own, read from concept_boy_head2.jpg's top-row back view (x 2174..2670 of 2752); the
    # under-shell is painted with a patch of that view, its broad light taken out: the first pass drew it as even
    # strands, which showed as faint straight streaks over the crown)
    sh = "concept_boy_head2.jpg"
    pal = dict(fixed=pal, sheet=dict(src=sh, box=(2200, 80, 2650, 520), key="blond", darken=1.16, saturate=0.92, lit=0.65,
                                        tint=(1.06, 1.06, 1.02)))
    tiles = [
        # (the under-shell painted by script in the sheet's colours: the patch lifted from the sheet showed as grey-olive
        # patches on the crown from above)
        dict(base=True, strands=4, rag=0.5),
        dict(bend=0.35, width=0.78, taper=0.8, length=1.0, light=0.7, strands=8, rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
        dict(bend=-0.3, width=0.78, taper=0.8, length=1.0, light=0.7, strands=8, rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
        dict(wave=0.18, width=0.75, taper=0.8, length=1.0, light=0.8, strands=8, rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
        dict(bend=0.15, curl=0.9, curl_start=0.55, width=0.72, taper=0.8, length=0.98, light=0.8, strands=7,
             rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
        dict(bend=-0.15, curl=-0.9, curl_start=0.55, width=0.72, taper=0.8, length=0.98, light=0.8, strands=7,
             rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
        dict(curl=1.3, curl_start=0.45, width=0.7, taper=0.8, length=0.95, light=0.9, strands=6, rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
        dict(curl=-1.3, curl_start=0.45, width=0.7, taper=0.8, length=0.95, light=0.9, strands=6, rag=0.22, tufts=2, soft=0.3, side_soft=0.25),
    ]
    return pal, tiles, {"hair": hair}


def captain():
    # A full white beard and moustache, white-grey hair in a fringe round the back and sides under his cap, heavy grey
    # brows (the user); concept_captain_head.jpg (the beard, the cap on), concept_captain_head_bare.jpg (the fringe).
    # Second pass (2026-11-18), to the sheet: the beard a full ROUNDED soft near-white mass, warm grey only in its
    # shadows, wider than the jaw, its lower edge a few big soft points; a drooping walrus moustache in two lobes; heavy
    # bushy brows that overhang the eyes; the fringe thinning upward into the bald crown in sparse wisps.
    fixed = [(0.5, 0.47, 0.42), (0.64, 0.61, 0.56), (0.76, 0.74, 0.69), (0.86, 0.85, 0.81), (0.93, 0.92, 0.89)]
    pal = dict(fixed=fixed, sheet=dict(src="concept_captain_head.jpg", box=(230, 590, 600, 830), key="grey",
                                       darken=1.32, saturate=1.1))
    down = Vector((0, 0, -1))
    beard = dict(
        # (angles from the jaw's middle, about the mouth's height, 0.09 back; the skin is read no further than 0.62
        # head sizes from there, so under the chin the beard closes round instead of following the throat down)
        centre=(0.09, -0.32, 0.78),
        # the cheek line (top) and how far under the chin and down the jaw it reaches (bottom); in front of the ear
        # it runs up as a sideburn to the cap
        high=lambda a: pw([(0, -13), (14, -12), (24, -4), (40, 6), (60, 10), (80, 18), (95, 24), (102, 18), (106, 10)], abs(a)),
        low=lambda a: pw([(0, -70), (40, -66), (70, -58), (88, -48), (98, -30), (106, -6)], abs(a)),
        reach=106,
        fall=lambda a: 3.0 * math.sin(a * 0.3) + pw([(0, -78), (30, -75), (60, -66), (90, -52), (106, -26)], abs(a)),
        # how far the beard stands off: full round the chin and the jaw (wider than the jaw), close on the cheeks,
        # thinning to nothing at the sideburn's back edge (no cut in front of the ear)
        thick=lambda a, e: (0.06 + 0.2 * sstep(-8, -40, e) * sstep(112, 40, abs(a))) * sstep(110, 92, abs(a))
        * (1.0 - 0.35 * sstep(-58, -70, e)) + 0.012,
        comb=lambda a, e, d: down + Vector((0, -0.25, 0)) + d * 0.2,
        # (a soft shadow under the moustache: the beard's locks rooted just below it darker)
        shade_at=lambda a, e: 1.0 - 0.3 * sstep(40, 15, abs(a)) * sstep(-42, -24, e),
        # FOURTH PASS: ONE smooth rounded shell (the hull's normals: one soft mass), painted with broad soft lock bands
        # (tile 0's soft strokes), its lower edge and cheek line a SOFT band (tile 0's lower half: alpha falling off in
        # a few broad points, dithered by the shader's feather), and only a FEW large soft-edged cards (8) round the
        # lower outline to break it into big soft points. The third pass's 20 jagged cards read as paper flakes.
        shell_cols=16, shell_rows=6, shell_frac=0.92, shell_shade=0.94, top_band=True, shell_band=6.0, shell_tile=4,
        shell_past=0.0, shell_top=90.0,
        layers=[
            dict(count=6, band=(0.0, 0.3), spacing=26, length=(0.34, 0.42), width=(0.42, 0.5), tiles=[1, 2],
                 depth=(0.75, 0.9), lift=(0.0, 0.0), shade=0.96, spin=0.0, clump=0.0, cup=0.28),
        ],
        # (what it follows, for the face rig: the jaw under and round the chin, fading to the head up the cheeks and
        # the sideburns)
        jaw=lambda a, e: sstep(100, 72, abs(a)) * sstep(14, -6, e),
    )
    moustache = dict(
        # (a big drooping walrus moustache over the mouth: two full lobes from a parting under the nose)
        centre=(0.09, -0.32),
        high=lambda a: pw([(0, 3), (14, -2), (28, -14), (44, -32)], abs(a)),
        low=lambda a: pw([(0, -16), (14, -22), (28, -34), (44, -50)], abs(a)),
        gap=2.0, reach=44,
        fall=lambda a: pw([(0, -26), (20, -40), (46, -56)], abs(a)),
        # (fourth pass: thicker than the beard everywhere they meet, so the walrus stands out of it as its own mass)
        thick=lambda a, e: (0.17 + 0.12 * sstep(2, 16, abs(a))) * sstep(46, 30, abs(a)) * (0.5 + 0.5 * sstep(2, 8, abs(a))),
        comb=lambda a, e, d: Vector((0.55 * math.copysign(1.0, a), -0.15, -0.9)),
        # (fourth pass: the two lobes are the smooth shell, lighter than the beard, and only two big soft cards a side
        # at the drooping ends; the beard's locks under it are darker (shade_at): the soft shadow that parts them)
        shell_cols=12, shell_rows=5, shell_frac=0.95, shell_shade=1.0, top_band=True, shell_band=3.0, shell_tile=5,
        shell_past=0.0, shell_top=90.0,
        layers=[],
        # (it follows the upper lip: the head, not the jaw)
        jaw=lambda a, e: 0.0,
    )
    c_high = lambda a: 3.0 * math.sin(a * 0.41) + pw([(78, 10), (95, 24), (120, 30), (180, 30)], abs(a))
    c_low = lambda a: pw([(78, 5), (96, 6), (104, 6), (122, 0), (134, -22), (155, -32), (180, -35)], abs(a))

    def cap_locks(rng):
        out = []

        def add(a, share, length, width, swing, depth, rows=3):
            a = a + rng.uniform(-5, 5)
            lo, hi = c_low(a), c_high(a)
            out.append(dict(a=a, e=lo + (hi - lo) * (share + rng.uniform(-0.05, 0.05)),
                            comb=lambda d: Vector((0, 1.0, -0.55)), length=length * rng.uniform(0.85, 1.15),
                            width=width * rng.uniform(0.9, 1.1), curl=0.5 * rng.uniform(0.6, 1.2), curl_from=0.55,
                            swing=swing, depth=depth, shade=rng.uniform(0.93, 1.0), rows=rows, crest=0.18,
                            edge=0.9, tip=0.35, tile=7, hull=0.75))
        # the upper row, round from just behind the temples to the back, swept back and down to the nape's middle
        for a in (100, 116, 132, 148, 164):
            for sg in (1, -1):
                add(sg * a, 0.45, 0.3, 0.32, -sg * 0.25, (0.45, 0.95))
        add(180, 0.45, 0.3, 0.32, 0.0, (0.45, 0.95))
        return out

    hair = dict(
        # the fringe: round the back and sides from the temples, swept back; full low down, thinning upward to
        # nothing, its top edge broken by sparse wisps into the bald crown (with the cap off it must not read as a
        # headband); under the cap nothing comes through (under_cap: points are pulled inside it)
        under_cap=True,
        high=lambda a: 3.0 * math.sin(a * 0.41) + pw([(78, 10), (95, 24), (120, 30), (180, 30)], abs(a)),
        low=lambda a: pw([(78, 5), (96, 6), (104, 6), (122, 0), (134, -22), (155, -32), (180, -35)], abs(a)),
        gap=78,
        fall=lambda a: 2.5 * math.sin(a * 0.37) + pw([(50, 0), (70, -4), (96, 4), (122, -4), (134, -28), (180, -41)],
                                                     abs(a)),
        thick=lambda a, e: (0.025 + 0.11 * sstep(22, 2, e) * pw([(80, 0.5), (100, 1.0), (180, 1.15)], abs(a))) * (0.4 + 0.6 * sstep(78, 95, abs(a))),
        comb=lambda a, e, d: Vector((0, 1.0, -0.55)),
        shell_cols=22, shell_rows=5, shell_frac=0.85, shell_shade=0.92, top_band=True, shell_band=12.0,
        shell_top=90.0,
        # (third pass: the cards read as a band of shards; the fringe is now soft FLAT MODELLED LOCKS swept back and
        # down (as the bare sheet and the swimming pose paint it), low crests, light bellies, a slight flick at the
        # end; no wisps over the crown (thin locks there read as lines across the bald head): the top edge feathers
        # through the under-shell's taller band of strands)
        # (fourth pass: no modelled locks: they read as a laurel wreath of leaves with dark notches; the fringe is the
        # smooth shell alone (one soft mass), painted with soft swept strokes, both its edges soft bands that
        # feather out through the shader's dither. cap_locks is kept for a later try.)
        layers=[],
    )
    brows = dict(
        # (heavy and bushy, standing out over the eyes)
        high=lambda a: pw([(10, 10), (30, 12), (46, 6)], abs(a)),
        low=lambda a: pw([(10, -1), (30, 1), (46, -2)], abs(a)),
        gap=8, reach=46,
        fall=lambda a: -9.0,
        thick=lambda a, e: 0.08 * (0.6 + 0.4 * sstep(10, 26, abs(a))),
        comb=lambda a, e, d: Vector((math.copysign(1.0, a), -0.45, 0.1)),
        # (fourth pass: each brow a small soft shell (a bushy tuft) and three big soft cards out over the eye; the
        # third pass's ten pointed cards read as feathers)
        shell_cols=8, shell_rows=2, shell_frac=0.8, shell_shade=0.98, top_band=True, shell_band=3.0,
        shell_past=0.0, shell_top=90.0,
        layers=[
            dict(count=6, band=(0.2, 0.9), spacing=10, length=(0.2, 0.24), width=(0.2, 0.24), tiles=[3],
                 depth=(0.7, 1.05), lift=(0.0, 0.02), shade=1.0, spin=0.0, rows=2, clump=0.0, cup=0.15),
        ],
    )
    # (the under-shell painted with the fringe of concept_captain_head_bare.jpg's back view (3168 x 1344), its
    # broad light taken out; the locks drawn by script in the beard's own colours, low in contrast)
    tiles = [
        # (fourth pass: the fringe's under-shell painted by script, soft strokes; the patch lifted from the bare sheet
        # carried its dark strokes and a line of skin)
        dict(base=True, strands=3, rag=0.25, strokes=True, soft=0.35, points=1.3),
        # (fourth pass: big soft-edged points: the beard's outline cards, then the moustache's and brows')
        dict(wave=0.1, width=0.9, taper=0.7, length=1.0, light=0.2, strands=9, rag=0.0, tufts=1, soft=0.45),
        dict(wave=-0.1, bend=0.15, width=0.9, taper=0.7, length=1.0, light=0.2, strands=9, rag=0.0, tufts=1, soft=0.45),
        dict(bend=0.25, width=0.9, taper=0.72, length=1.0, light=0.3, strands=8, rag=0.0, tufts=1, soft=0.45),
        # (the beard's shell: soft broad strokes, low in contrast, its edge a soft band of a few broad points)
        dict(base=True, strands=3, rag=0.22, strokes=True, soft=0.35, points=1.2, brighten=0.08),
        # (the moustache's shell: lighter than the beard, a clean soft surface)
        dict(base=True, strands=3, rag=0.3, strokes=True, soft=0.4, points=1.0, brighten=0.1),
        dict(bend=0.3, width=0.95, taper=0.65, length=0.9, light=0.35, strands=7, rag=0.12, tufts=1),
        # (the fringe's modelled locks)
        dict(surface=dict(grooves=3.0, lo=0.55, hi=0.85, streak=0.04)),
    ]
    return pal, tiles, {"hair": hair, "beard": beard, "moustache": moustache, "brows": brows}


FIGURES = {"brother": brother, "boy": boy, "captain": captain}


def build(fig):
    rng = random.Random(7)
    nrng = np.random.default_rng(11)
    head = Head(fig)
    pal, tiles, masses = FIGURES[fig]()
    if isinstance(pal, dict):
        # (the colours taken from the figure's concept sheet; with --scripted the fixed ones written beside them)
        pal = pal["fixed"] if SCRIPTED else palette_from(**pal["sheet"])
    print("HAIR palette", [tuple(round(x, 2) for x in c) for c in pal])
    img = np.zeros((ATLAS, ATLAS, 4))
    for i, t in enumerate(tiles):
        # (the lock painted by script (its shape and light), then whatever is lifted from the sheet laid over it)
        if "surface" in t:
            paint_surface(img, i, pal, nrng, **t["surface"])
        elif "else" in t or "lift" not in t:
            paint_lock(img, i, pal, nrng, **t.get("else", t))
        if "lift" in t and not SCRIPTED:
            for part in t["lift"]:
                lift(img, i, **part)
    os.makedirs(os.path.join(ROOT, "textures", "hair"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "models", "hair"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "blend", "hair"), exist_ok=True)
    im = save_image(img, fig + "_locks", os.path.join(ROOT, "textures", "hair", fig + "_locks.png"))
    mat = bpy.data.materials.new(fig + "_hair")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = im
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    for o in list(bpy.data.objects):
        o.hide_set(True)
    for piece, mass in masses.items():
        b = Builder(head.recentred(*mass["centre"]) if "centre" in mass else head, mass, rng)
        if mass.get("under_cap") and head.cap is not None:
            b.cap = head.cap
        b.build()
        ob = b.to_object(fig + "_" + piece, mat)
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print("HAIR", fig, piece, "triangles", tris)
        bpy.ops.object.select_all(action="DESELECT")
        ob.hide_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "models", "hair", fig + "_" + piece + ".glb"),
                                  export_format="GLB", use_selection=True, export_yup=True, export_normals=True,
                                  export_tangents=False, export_vertex_color="ACTIVE", export_attributes=True,
                                  export_materials="EXPORT",
                                  export_image_format="NONE")
    # (keep only the hair in the .blend)
    for o in list(bpy.data.objects):
        if not any(o.name == fig + "_" + p for p in masses):
            bpy.data.objects.remove(o)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0  # (no .blend1 copies beside it)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "blend", "hair", fig + ".blend"), compress=True)


SCRIPTED = False

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
    # (--scripted: the locks painted by script only, the fallback, to compare with the ones lifted from the sheets)
    SCRIPTED = "--scripted" in args
    args = [a for a in args if not a.startswith("--")] or ["all"]
    for f in (FIGURES if args[0] == "all" else args):
        build(f)
