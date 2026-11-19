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
Shader: shaders/hair_cards.gdshader (new, alpha scissor, two-sided with the hull's normal kept on back faces).
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
        body = bpy.data.objects[fig + "_body"]
        dg = bpy.context.evaluated_depsgraph_get()
        me = body.evaluated_get(dg).to_mesh()
        mw = body.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        self.bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
        g = body.vertex_groups["head"].index
        hv = [verts[v.index] for v in body.data.vertices if any(x.group == g and x.weight > 0.5 for x in v.groups)]
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

    def recentred(self, dy, dz):
        """The same head read from another middle (dy back, dz up, in head sizes): a beard is read from the jaw's
        middle, where rays meet the jaw, the chin's underside and the throat instead of passing under them."""
        h = copy.copy(self)
        h.c = self.c + Vector((0.0, dy * self.size, dz * self.size))
        h._rays()
        return h

    def _rays(self):
        reach = 2.2 * self.size
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
               rag=0.3, strands=9, light=0.6, base=False, gloss_at=0.45, taper=0.85, tufts=3, curly=False, strokes=False):
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
                tone = np.where(inside_s, 0.46 + 0.22 * body * np.clip(1.2 - v, 0, 1), tone)
                tone = tone - 0.08 * ((v > 1.0) & (v < 1.15) & (np.abs(u) < 0.5))
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
                lo = m["low"](a) - m.get("shell_past", 3.0)
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
                uvs = [tile_uv(0, s0, t0), tile_uv(0, s0, t1), tile_uv(0, s1, t1), tile_uv(0, s1, t0)]
                shade = m.get("shell_shade", 0.45)
                g0, g1 = 0.5 + 0.5 * r / rows, 0.5 + 0.5 * (r + 1) / rows
                cl = [(shade, g0, 0, 1), (shade, g1, 0, 1), (shade, g1, 0, 1), (shade, g0, 0, 1)]
                self.add([p00, p01, p11, p10], uvs, cl, [n00, n01, n11, n10])
            # (a fan to the top, when the shell reaches it)
            hi0 = min(m.get("high", lambda _a: 91.0)(a0), m.get("shell_top", 86.0))
            if hi0 >= m.get("shell_top", 86.0) - 0.1:
                dtop = direction(0, 90)
                ptop = self.h.c + dtop * (self.h.skin(dtop) + self.thick(dtop) * m["shell_frac"] + 0.002)
                ntop = self.hull_normal(dtop)
                (p00, n00, _), (p10, n10, _) = ring[0][0], ring[1][0]
                uvs = [tile_uv(0, 0.5, 0.0), tile_uv(0, 0, 0.05), tile_uv(0, 1, 0.05)]
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
            g = m["comb"](a, e, d)
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
        shade = layer["shade"]
        spin = rng.uniform(-1, 1) * layer.get("spin", 0.0)
        rowsets = []
        for r, d in enumerate(dirs):
            t = r / rows
            a, e = angles(d)
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
                nn = self.hull_normal(q - self.h.c).lerp(n, 0.5).normalized()
                su = (1 - s) if flip else s
                row.append((q, tile_uv(tile, su, t), (shade, t, 1, 1), nn))
            rowsets.append(row)
        for r in range(rows):
            for c in range(2):
                corners = [rowsets[r][c], rowsets[r + 1][c], rowsets[r + 1][c + 1], rowsets[r][c + 1]]
                self.add([x[0] for x in corners], [x[1] for x in corners], [x[2] for x in corners],
                         [x[3] for x in corners])

    def build(self):
        if self.m.get("shell_cols"):
            self.shell()
        print("HAIR shell faces", len(self.faces))
        for layer in self.m["layers"]:
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
    # Thick tousled mop of curls, shorter at the sides, falling on the forehead (the user); concept_brother_head2.jpg.
    pal = [(0.12, 0.075, 0.055), (0.27, 0.17, 0.1), (0.41, 0.26, 0.15), (0.6, 0.36, 0.18), (0.8, 0.5, 0.26)]
    hair = dict(
        # hairline: elevation the hair reaches down to, by azimuth (0 = the face): forehead, temple, before the ear,
        # over the ear, behind it, the nape
        low=lambda a: pw([(0, 26), (25, 26), (45, 17), (60, 5), (75, -4), (100, -6), (108, -2), (128, -2), (138, -14),
                          (150, -34), (180, -44)], abs(a)),
        # how far down a lock may fall (a wobble, so the fringe is not cut straight)
        fall=lambda a: 3.5 * math.sin(a * 0.21) + pw([(0, 8), (30, 10), (45, 6), (60, -2), (75, -8), (100, -8), (108, -4),
                                                       (128, -4), (138, -18), (150, -42), (180, -50)], abs(a)),
        # thickness of the mop off the head (in head sizes): full on top, short at the sides, thinner at the nape
        thick=lambda a, e: lerp(pw([(0, 0.2), (60, 0.24), (100, 0.15), (130, 0.22), (180, 0.24)], abs(a)), 0.5,
                                sstep(15, 70, e)) * (0.35 + 0.65 * sstep(-35, 20, e)),
        comb=comb_from(direction(180, 62), 0.25, 0.0),
        shell_cols=20, shell_rows=5, shell_frac=0.85, shell_shade=0.85,
        layers=[
            dict(count=26, band=(0.0, 0.75), spacing=21, length=(0.5, 0.65), width=(0.4, 0.5), tiles=[1, 2, 3],
                 depth=(0.5, 0.95), lift=(0.0, 0.04), shade=0.8, spin=0.2),
            # (the fringe: curls from the front hairline hanging over the forehead, over the shell's edge)
            dict(count=13, band=(0.0, 0.22), arc=75, spacing=12, length=(0.42, 0.62), width=(0.36, 0.46),
                 tiles=[1, 2, 4, 5], depth=(0.5, 0.3), lift=(0.0, 0.02), shade=0.9, spin=0.15),
            dict(count=26, band=(0.15, 1.0), spacing=19, length=(0.45, 0.6), width=(0.4, 0.5), tiles=[1, 2, 4, 5],
                 depth=(0.7, 1.05), lift=(0.02, 0.06), shade=0.92, spin=0.3),
            dict(count=30, rows=2, band=(0.2, 1.0), spacing=16, length=(0.34, 0.46), width=(0.34, 0.42), tiles=[4, 5, 6, 7],
                 depth=(0.8, 1.1), lift=(0.0, 0.03), shade=1.0, spin=0.35),
        ],
    )
    tiles = [
        dict(base=True, strands=3, rag=0.45, curly=True),
        dict(curl=3.6, curl_start=0.5, width=0.8, taper=0.7, length=1.0, light=0.8, strands=8, bend=0.15, rag=0.3),
        dict(curl=-3.4, curl_start=0.45, width=0.8, taper=0.7, length=1.0, light=0.7, strands=8, bend=-0.15, rag=0.3),
        dict(wave=0.3, width=0.78, taper=0.7, length=1.0, light=0.8, strands=8, curl=2.0, curl_start=0.7, rag=0.35),
        dict(curl=4.2, curl_start=0.4, width=0.76, taper=0.72, length=0.95, light=1.0, strands=7, rag=0.3),
        dict(curl=-4.0, curl_start=0.35, width=0.76, taper=0.72, length=0.95, light=0.9, strands=7, bend=0.2, rag=0.3),
        dict(curl=4.8, curl_start=0.3, width=0.72, taper=0.75, length=0.9, light=1.1, strands=6, bend=-0.2, tufts=2),
        dict(curl=-4.6, curl_start=0.3, width=0.72, taper=0.75, length=0.9, light=1.1, strands=6, tufts=2),
    ]
    # A thin young moustache (the user), read from the jaw's middle like the captain's; the stubble is left to the face
    # paint (a faint tint there), not cards: at the game's half-size picture single hairs only shimmer.
    moustache = dict(
        centre=(0.09, -0.32),
        high=lambda a: pw([(0, -3), (14, -5), (24, -9)], abs(a)),
        low=lambda a: pw([(0, -8), (14, -10), (24, -14)], abs(a)),
        reach=25,
        fall=lambda a: pw([(0, -11), (24, -19)], abs(a)),
        thick=lambda a, e: 0.025,
        comb=lambda a, e, d: Vector((math.copysign(1.0, a) if abs(a) > 2 else 0.0, -0.1, -0.7)),
        shell_cols=6, shell_rows=2, shell_frac=0.6, shell_shade=0.8, top_band=True, shell_band=2.0,
        shell_past=0.0, shell_top=90.0,
        layers=[
            dict(count=8, band=(0.0, 1.0), spacing=5, length=(0.07, 0.1), width=(0.07, 0.09), tiles=[3],
                 depth=(0.5, 1.0), lift=(0.0, 0.0), shade=0.9, spin=0.05, rows=2),
        ],
    )
    return pal, tiles, {"hair": hair, "moustache": moustache}


def boy():
    # A fresh blond tousled mop (the user); concept_boy_head2.jpg: a fringe to the brows, the ears out, the nape
    # covered, straight locks breaking into pointed tips all round.
    pal = [(0.44, 0.34, 0.18), (0.66, 0.53, 0.31), (0.81, 0.68, 0.42), (0.91, 0.81, 0.56), (0.98, 0.93, 0.72)]
    hair = dict(
        low=lambda a: pw([(0, 30), (30, 28), (55, 14), (75, 2), (98, -2), (106, 8), (128, 6), (140, -16),
                          (160, -36), (180, -42)], abs(a)),
        fall=lambda a: 3.0 * math.sin(a * 0.23) + pw([(0, 10), (30, 9), (55, 0), (75, -8), (98, -6), (106, 4),
                                                       (128, 2), (140, -22), (160, -44), (180, -50)], abs(a)),
        thick=lambda a, e: lerp(pw([(0, 0.18), (60, 0.24), (100, 0.16), (130, 0.24), (180, 0.22)], abs(a)), 0.34,
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
    tiles = [
        dict(base=True, strands=4, rag=0.5),
        dict(bend=0.35, width=0.78, taper=0.92, length=1.0, light=0.7, strands=8, rag=0.35, tufts=3),
        dict(bend=-0.3, width=0.78, taper=0.92, length=1.0, light=0.7, strands=8, rag=0.35, tufts=3),
        dict(wave=0.18, width=0.75, taper=0.92, length=1.0, light=0.8, strands=8, rag=0.4, tufts=3),
        dict(bend=0.15, curl=0.9, curl_start=0.55, width=0.72, taper=0.94, length=0.98, light=0.8, strands=7,
             rag=0.35, tufts=2),
        dict(bend=-0.15, curl=-0.9, curl_start=0.55, width=0.72, taper=0.94, length=0.98, light=0.8, strands=7,
             rag=0.35, tufts=2),
        dict(curl=1.3, curl_start=0.45, width=0.7, taper=0.95, length=0.95, light=0.9, strands=6, rag=0.3, tufts=2),
        dict(curl=-1.3, curl_start=0.45, width=0.7, taper=0.95, length=0.95, light=0.9, strands=6, rag=0.3, tufts=2),
    ]
    return pal, tiles, {"hair": hair}


def captain():
    # A full white beard and moustache, white-grey hair in a fringe round the back and sides under his cap, heavy grey
    # brows (the user); concept_captain_head.jpg (the beard, the cap on), concept_captain_head_bare.jpg (the fringe).
    # Warm greys, not white: the earlier rounds came out "too white" and flat.
    pal = [(0.42, 0.41, 0.38), (0.58, 0.57, 0.53), (0.71, 0.7, 0.66), (0.82, 0.81, 0.77), (0.91, 0.9, 0.87)]
    down = Vector((0, 0, -1))
    beard = dict(
        # the cheek line (top) and how far under the chin and down the jaw it reaches (bottom); in front of the ear
        # it runs up as a sideburn to the cap
        # (angles from the jaw's middle, about the nose's height: see centre)
        centre=(0.09, -0.32),
        high=lambda a: pw([(0, -13), (14, -12), (24, -4), (40, 6), (60, 10), (80, 18), (95, 28), (102, 28)], abs(a)),
        low=lambda a: pw([(0, -58), (40, -57), (70, -53), (88, -46), (98, -30), (105, -6)], abs(a)),
        reach=105,
        fall=lambda a: pw([(0, -67), (60, -64), (90, -54), (105, -26)], abs(a)),
        # how far the beard stands off: full at the chin and hanging below it, close on the cheeks and sideburns
        thick=lambda a, e: (0.05 + 0.17 * sstep(-15, -40, e) * sstep(108, 15, abs(a)))
        * (1.0 - 0.5 * sstep(-55, -65, e)),
        comb=lambda a, e, d: down + Vector((0, -0.25, 0)) + d * 0.15,
        shell_cols=16, shell_rows=6, shell_frac=0.85, shell_shade=0.85, top_band=True, shell_band=6.0,
        shell_past=0.0, shell_top=90.0,
        layers=[
            dict(count=22, band=(0.0, 0.8), spacing=13, length=(0.24, 0.34), width=(0.24, 0.3), tiles=[1, 2, 3],
                 depth=(0.55, 1.0), lift=(0.0, 0.02), shade=0.92, spin=0.1),
            dict(count=22, band=(0.15, 1.0), spacing=12, length=(0.2, 0.3), width=(0.2, 0.26), tiles=[1, 2, 3],
                 depth=(0.8, 1.12), lift=(0.0, 0.03), shade=1.0, spin=0.25),
        ],
    )
    moustache = dict(
        centre=(0.09, -0.32),
        high=lambda a: pw([(0, -2), (20, -4), (34, -10)], abs(a)),
        low=lambda a: pw([(0, -10), (20, -13), (34, -18)], abs(a)),
        reach=34,
        fall=lambda a: pw([(0, -14), (20, -24), (40, -32)], abs(a)),
        thick=lambda a, e: 0.07,
        comb=lambda a, e, d: Vector((math.copysign(1.0, a) if abs(a) > 2 else 0.0, -0.1, -0.9)),
        shell_cols=8, shell_rows=3, shell_frac=0.7, shell_shade=0.85, top_band=True, shell_band=4.0,
        shell_past=0.0, shell_top=90.0,
        layers=[
            dict(count=12, band=(0.0, 1.0), spacing=6, length=(0.16, 0.24), width=(0.13, 0.17), tiles=[4, 5],
                 depth=(0.6, 1.1), lift=(0.0, 0.01), shade=0.95, spin=0.15, rows=2),
        ],
    )
    hair = dict(
        # the fringe: round the back and sides from the temples, swept back; thin at its top, where the cap fits
        # close (so it stays inside the cap), full below the cap's edge
        high=lambda a: pw([(50, 14), (70, 24), (100, 30), (140, 32), (180, 30)], abs(a)),
        low=lambda a: pw([(50, 6), (70, 2), (96, 8), (104, 6), (122, 4), (134, -16), (155, -24), (180, -26)], abs(a)),
        gap=50,
        fall=lambda a: pw([(50, 0), (70, -4), (96, 4), (122, 0), (134, -22), (180, -32)], abs(a)),
        thick=lambda a, e: 0.03 + 0.07 * sstep(14, 4, e),
        comb=lambda a, e, d: Vector((0, 1.0, -0.55)),
        shell_cols=22, shell_rows=4, shell_frac=0.8, shell_shade=0.85, top_band=True, shell_band=6.0,
        shell_top=90.0,
        layers=[
            dict(count=26, band=(0.0, 0.85), spacing=13, length=(0.22, 0.32), width=(0.2, 0.26), tiles=[7, 1],
                 depth=(0.5, 1.05), lift=(0.0, 0.0), shade=0.9, spin=0.1, rows=2),
        ],
    )
    brows = dict(
        high=lambda a: pw([(10, 6), (30, 8), (55, 4)], abs(a)),
        low=lambda a: pw([(10, -2), (30, 0), (55, -4)], abs(a)),
        gap=9, reach=52,
        fall=lambda a: -10.0,
        thick=lambda a, e: 0.05,
        comb=lambda a, e, d: Vector((math.copysign(1.0, a), -0.2, 0.35)),
        layers=[
            dict(count=18, band=(0.0, 1.0), spacing=5, length=(0.1, 0.14), width=(0.09, 0.12), tiles=[6],
                 depth=(0.5, 1.2), lift=(0.0, 0.01), shade=1.0, spin=0.1, rows=2),
        ],
    )
    tiles = [
        dict(base=True, strands=4, rag=0.5, strokes=True),
        dict(wave=0.22, width=0.86, taper=0.8, length=1.0, light=0.35, strands=9, rag=0.4, tufts=3),
        dict(wave=-0.2, bend=0.15, width=0.86, taper=0.8, length=1.0, light=0.35, strands=9, rag=0.4, tufts=3),
        dict(wave=0.12, bend=-0.2, width=0.8, taper=0.85, length=1.0, light=0.4, strands=8, rag=0.45, tufts=4),
        dict(curl=1.1, curl_start=0.3, width=0.8, taper=0.92, length=1.0, light=0.7, strands=8, rag=0.3, tufts=2),
        dict(curl=-1.1, curl_start=0.3, width=0.8, taper=0.92, length=1.0, light=0.7, strands=8, rag=0.3, tufts=2),
        dict(bend=0.3, width=0.9, taper=0.7, length=0.9, light=0.5, strands=7, rag=0.55, tufts=4),
        dict(bend=0.1, width=0.8, taper=0.88, length=1.0, light=0.6, strands=8, rag=0.4, tufts=3),
    ]
    return pal, tiles, {"hair": hair, "beard": beard, "moustache": moustache, "brows": brows}


FIGURES = {"brother": brother, "boy": boy, "captain": captain}


def build(fig):
    rng = random.Random(7)
    nrng = np.random.default_rng(11)
    head = Head(fig)
    pal, tiles, masses = FIGURES[fig]()
    img = np.zeros((ATLAS, ATLAS, 4))
    for i, t in enumerate(tiles):
        paint_lock(img, i, pal, nrng, **t)
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
                                  export_tangents=False, export_vertex_color="ACTIVE", export_materials="EXPORT",
                                  export_image_format="NONE")
    # (keep only the hair in the .blend)
    for o in list(bpy.data.objects):
        if not any(o.name == fig + "_" + p for p in masses):
            bpy.data.objects.remove(o)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0  # (no .blend1 copies beside it)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "blend", "hair", fig + ".blend"), compress=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
    for f in (FIGURES if args[0] == "all" else args):
        build(f)
