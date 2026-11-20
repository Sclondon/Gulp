// Injected into the page by tools/mem_load.js before any of the game's scripts run. Counts what the
// page holds: the WASM heap (Godot's memory), and every WebGL texture, buffer and renderbuffer by
// the bytes it was given (the GPU's share, as the page asked for it), each with its peak.
// With window.__phone set (mem_load.js PHONE=1) it also hides the S3TC/BPTC/RGTC texture extensions,
// as iOS WebKit has none of them, so Godot takes the same path it takes on an iPhone.
(() => {
  const HIDE = /s3tc|bptc|rgtc/i;
  const phone = !!window.__phone;
  const m = { wasm: 0, wasmPeak: 0, tex: 0, buf: 0, rb: 0, gl: 0, glPeak: 0, texPeak: 0, bufPeak: 0, texCount: 0, bufCount: 0,
    texBig: [], hidden: phone, formats: {} };
  window.__mem = m;
  const mems = [];
  const keep = (x) => { if (x instanceof WebAssembly.Memory && !mems.includes(x)) mems.push(x); };
  const scan = (inst) => { try { for (const v of Object.values(inst.exports)) keep(v); } catch (e) {} };
  const OrigMemory = WebAssembly.Memory;
  WebAssembly.Memory = function (d) { const x = new OrigMemory(d); keep(x); return x; };
  WebAssembly.Memory.prototype = OrigMemory.prototype;
  for (const name of ['instantiate', 'instantiateStreaming']) {
    const orig = WebAssembly[name];
    WebAssembly[name] = function (...a) {
      return orig.apply(this, a).then((r) => { scan(r.instance || r); return r; });
    };
  }
  const poll = () => {
    let w = 0;
    for (const x of mems) w += x.buffer.byteLength;
    m.wasm = w;
    if (w > m.wasmPeak) m.wasmPeak = w;
  };
  setInterval(poll, 200);
  m.poll = poll;

  const G = WebGL2RenderingContext.prototype;
  const bpp = (ifmt, fmt, type) => {
    const t = {
      0x8058: 4, 0x8C43: 4, 0x8051: 4, 0x881A: 8, 0x8814: 16, 0x8229: 1, 0x822B: 2, 0x822D: 2, 0x822F: 4, 0x822E: 4,
      0x8230: 8, 0x88F0: 4, 0x81A6: 4, 0x8CAC: 4, 0x8059: 4, 0x8C3A: 4, 0x8D62: 2, 0x8056: 2, 0x8057: 2, 0x81A5: 2,
      0x8C3D: 4, 0x8815: 12, 0x881B: 6, 0x8D7C: 4, 0x8D8E: 4, 0x8D70: 16, 0x8D82: 16, 0x8D23: 3, 0x8D76: 3,
    };
    if (t[ifmt]) return t[ifmt];
    if (ifmt === 0x1908 || ifmt === 0x1907) return type === 0x1406 ? 16 : type === 0x140B ? 8 : 4; // RGBA/RGB unsized
    if (ifmt === 0x1909 || ifmt === 0x1906) return 1;
    if (ifmt === 0x190A) return 2;
    return 4;
  };
  const bound = new Map(); // unit:target -> texture
  let unit = 0;
  const key = (target) => unit + ':' + (target >= 0x8515 && target <= 0x851A ? 0x8513 : target);
  const total = () => {
    m.gl = m.tex + m.buf + m.rb;
    if (m.gl > m.glPeak) m.glPeak = m.gl;
    if (m.tex > m.texPeak) m.texPeak = m.tex;
    if (m.buf > m.bufPeak) m.bufPeak = m.buf;
  };
  const live = new Set();
  m.top = (n = 25) => [...live].map((t) => [Object.values(t.__b || {}).reduce((x, y) => x + y, 0), t.__label])
    .sort((x, y) => y[0] - x[0]).slice(0, n).map(([b, l]) => `${(b / 1048576).toFixed(1)}MB ${l}`);
  const setTex = (tex, slot, bytes, label) => {
    if (!tex) return;
    live.add(tex);
    tex.__b = tex.__b || {};
    const old = tex.__b[slot] || 0;
    tex.__b[slot] = bytes;
    m.tex += bytes - old;
    if (label !== undefined) tex.__label = label;
    total();
  };
  const wrap = (name, fn) => { const o = G[name]; if (o) G[name] = function (...a) { return fn.call(this, o, a); }; };
  wrap('activeTexture', function (o, a) { unit = a[0] - 0x84C0; return o.apply(this, a); });
  wrap('bindTexture', function (o, a) { bound.set(key(a[0]), a[1]); return o.apply(this, a); });
  wrap('createTexture', function (o, a) { m.texCount++; return o.apply(this, a); });
  wrap('deleteTexture', function (o, a) {
    const t = a[0];
    if (t && t.__b) { for (const v of Object.values(t.__b)) m.tex -= v; t.__b = {}; live.delete(t); }
    m.texCount--;
    return o.apply(this, a);
  });
  wrap('texStorage2D', function (o, a) {
    const [target, levels, ifmt, w, h] = a;
    let s = 0;
    for (let l = 0; l < levels; l++) s += Math.max(1, w >> l) * Math.max(1, h >> l);
    const faces = target === 0x8513 ? 6 : 1;
    const bytes = s * bpp(ifmt) * faces;
    m.formats[ifmt] = (m.formats[ifmt] || 0) + bytes;
    setTex(bound.get(key(target)), 'storage', bytes, `${w}x${h} ${ifmt.toString(16)} L${levels}`);
    return o.apply(this, a);
  });
  wrap('texStorage3D', function (o, a) {
    const [target, levels, ifmt, w, h, d] = a;
    let s = 0;
    for (let l = 0; l < levels; l++) s += Math.max(1, w >> l) * Math.max(1, h >> l) * (target === 0x8C1A ? d : Math.max(1, d >> l));
    const bytes = s * bpp(ifmt);
    m.formats[ifmt] = (m.formats[ifmt] || 0) + bytes;
    setTex(bound.get(key(target)), 'storage', bytes, `${w}x${h}x${d} ${ifmt.toString(16)}`);
    return o.apply(this, a);
  });
  wrap('texImage2D', function (o, a) {
    if (a.length >= 8) {
      const [target, level, ifmt, w, h, , fmt, type] = a;
      const bytes = w * h * bpp(ifmt, fmt, type);
      m.formats[ifmt] = (m.formats[ifmt] || 0) + bytes;
      setTex(bound.get(key(target)), target + ':' + level, bytes, level === 0 ? `${w}x${h} ${ifmt.toString(16)}` : undefined);
    }
    return o.apply(this, a);
  });
  wrap('texImage3D', function (o, a) {
    const [target, level, ifmt, w, h, d, , fmt, type] = a;
    setTex(bound.get(key(target)), 'l' + level, w * h * d * bpp(ifmt, fmt, type), `${w}x${h}x${d}`);
    return o.apply(this, a);
  });
  wrap('compressedTexImage2D', function (o, a) {
    const [target, level, ifmt, w, h, , data] = a;
    const bytes = data && data.byteLength ? data.byteLength : (a[6] || 0);
    m.formats['c' + ifmt] = (m.formats['c' + ifmt] || 0) + bytes;
    setTex(bound.get(key(target)), target + ':' + level, bytes, `${w}x${h} c${ifmt.toString(16)}`);
    return o.apply(this, a);
  });
  const bufBound = new Map();
  const liveBuf = new Set();
  m.topBuf = (n = 25) => { const by = {}; for (const b of liveBuf) { const k = Math.round((b.__b || 0) / 1024) + 'KB ' + b.__t; by[k] = (by[k] || 0) + 1; }
    return Object.entries(by).map(([k, c]) => [parseInt(k) * c, k + ' x' + c]).sort((x, y) => y[0] - x[0]).slice(0, n).map(([t, k]) => (t / 1024).toFixed(1) + 'MB ' + k); };
  wrap('bindBuffer', function (o, a) { bufBound.set(a[0], a[1]); return o.apply(this, a); });
  wrap('bindBufferBase', function (o, a) { bufBound.set(a[0], a[2]); return o.apply(this, a); });
  wrap('bindBufferRange', function (o, a) { bufBound.set(a[0], a[2]); return o.apply(this, a); });
  wrap('createBuffer', function (o, a) { m.bufCount++; return o.apply(this, a); });
  wrap('bufferData', function (o, a) {
    const b = bufBound.get(a[0]);
    const size = typeof a[1] === 'number' ? a[1] : (a[1] ? (a.length >= 5 && a[4] ? a[4] * (a[1].BYTES_PER_ELEMENT || 1) : a[1].byteLength) : 0);
    if (b) { m.buf += size - (b.__b || 0); b.__b = size; b.__t = a[0].toString(16); liveBuf.add(b); total(); }
    return o.apply(this, a);
  });
  wrap('deleteBuffer', function (o, a) {
    const b = a[0];
    if (b && b.__b) { m.buf -= b.__b; b.__b = 0; total(); }
    liveBuf.delete(b);
    m.bufCount--;
    return o.apply(this, a);
  });
  let rbBound = null;
  wrap('bindRenderbuffer', function (o, a) { rbBound = a[1]; return o.apply(this, a); });
  const rbStore = (samples, ifmt, w, h) => {
    if (!rbBound) return;
    const size = w * h * bpp(ifmt) * Math.max(1, samples);
    m.rb += size - (rbBound.__b || 0);
    rbBound.__b = size;
    total();
  };
  wrap('renderbufferStorage', function (o, a) { rbStore(1, a[1], a[2], a[3]); return o.apply(this, a); });
  wrap('renderbufferStorageMultisample', function (o, a) { rbStore(a[1], a[2], a[3], a[4]); return o.apply(this, a); });
  wrap('deleteRenderbuffer', function (o, a) {
    const r = a[0];
    if (r && r.__b) { m.rb -= r.__b; r.__b = 0; total(); }
    return o.apply(this, a);
  });
  if (phone) {
    for (const C of [WebGL2RenderingContext, WebGLRenderingContext]) {
      const P = C.prototype;
      const ge = P.getExtension, gs = P.getSupportedExtensions;
      P.getExtension = function (n) { return HIDE.test(n) ? null : ge.call(this, n); };
      P.getSupportedExtensions = function () { return (gs.call(this) || []).filter((n) => !HIDE.test(n)); };
    }
  }
})();
