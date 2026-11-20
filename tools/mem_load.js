// Loads a Gulp web build in the real Chrome and logs what the page holds while it loads (tools/PERF.md,
// "Memory on phones"): the WASM heap, the WebGL textures, buffers and renderbuffers (tools/mem_probe.js
// counts them as the page creates them), and the renderer's and GPU process's private memory.
//   node tools/serve_web.js <export folder> 8741
//   PHONE=1 node tools/mem_load.js http://127.0.0.1:8741/index.html <profile folder> <out.txt> [after ready s] [timeout s]
// PHONE=1 hides S3TC/BPTC/RGTC from the page as iOS WebKit has none (so Godot takes an iPhone's path).
// The window is shown (a minimized or hidden window runs one frame a second or none).
// Each line: s since opened, MEM wasm/peak, gl (tex+buf+rb)/peak, tex, buf, rb in MB; PROC renderer+gpu MB.
const { chromium } = require('C:/Projects/scareathon/trailer/node_modules/playwright-core');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const MB = (b) => (b / 1048576).toFixed(1);
(async () => {
  const [url, profile, out, afterS = '20', timeoutS = '600'] = process.argv.slice(2);
  const phone = process.env.PHONE === '1';
  const ctx = await chromium.launchPersistentContext(profile, {
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: false,
    viewport: { width: Number(process.env.W || 390), height: Number(process.env.H || 844) },
    args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--mute-audio', '--enable-precise-memory-info',
      ...(process.env.EXTRA ? process.env.EXTRA.split(' ') : [])],
  });
  await ctx.addInitScript({ content: (phone ? 'window.__phone = true;\n' : '') + fs.readFileSync(path.join(__dirname, 'mem_probe.js'), 'utf8') });
  const page = ctx.pages()[0] || await ctx.newPage();
  const t0 = Date.now();
  const lines = [];
  const now = () => ((Date.now() - t0) / 1000).toFixed(1);
  let ready = 0;
  let crashed = false;
  const write = () => fs.writeFileSync(out, lines.join('\n') + '\n');
  page.on('console', (msg) => {
    const s = msg.text();
    if (/GULP WARM \d+ ms/.test(s) && !/GULP MEM/.test(s)) return; // (each step: too many)
    lines.push(`${now()} ${msg.type()} ${s}`);
    if (/everything is ready/.test(s) && !ready) ready = Date.now();
  });
  page.on('crash', () => { crashed = true; lines.push(`${now()} PAGE CRASHED`); });
  page.on('pageerror', (e) => lines.push(`${now()} PAGEERROR ${e}`));
  // (the Chrome processes of this profile: the renderer and the GPU process, private bytes)
  const prof = path.basename(path.resolve(profile)).toLowerCase();
  const procMem = () => {
    try {
      const ps = `Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" | ? { $_.CommandLine -and $_.CommandLine.ToLower().Contains('${prof}') } | % { $t = if ($_.CommandLine -match '--type=([a-z-]+)') { $matches[1] } else { 'browser' }; \"$t $($_.PrivatePageCount)\" }`;
      const o = execFileSync('powershell', ['-NoProfile', '-Command', ps], { encoding: 'utf8', timeout: 8000 });
      const by = {};
      for (const l of o.split(/\r?\n/)) { const [t, b] = l.trim().split(' '); if (t) by[t] = (by[t] || 0) + Number(b); }
      return by;
    } catch (e) { return {}; }
  };
  const peak = { renderer: 0, 'gpu-process': 0 };
  await page.goto(url);
  const gl = await page.evaluate(() => {
    const c = document.createElement('canvas').getContext('webgl2');
    return [c.getSupportedExtensions().filter((n) => /compressed/.test(n)).join(','), screenX, outerWidth];
  });
  lines.push(`0 info COMPRESSED ${gl[0] || '(none)'} phone=${phone} screenX=${gl[1]}`);
  let tick = 0;
  while ((Date.now() - t0) / 1000 < Number(timeoutS) && !crashed) {
    await new Promise((r) => setTimeout(r, 1000));
    tick++;
    const m = await page.evaluate(() => { const x = window.__mem; x.poll(); const p = performance.memory || {}; return { ...x, js: p.usedJSHeapSize || 0, formats: x.formats }; }).catch(() => null);
    if (!m) { lines.push(`${now()} no answer from the page`); continue; }
    let pl = '';
    if (tick % 5 === 0) {
      const p = procMem();
      for (const k of Object.keys(peak)) if ((p[k] || 0) > peak[k]) peak[k] = p[k];
      pl = ` PROC renderer ${MB(p.renderer || 0)} gpu ${MB(p['gpu-process'] || 0)}`;
    }
    lines.push(`${now()} MEM wasm ${MB(m.wasm)}/${MB(m.wasmPeak)} gl ${MB(m.gl)}/${MB(m.glPeak)} tex ${MB(m.tex)} (${m.texCount}) buf ${MB(m.buf)} (${m.bufCount}) rb ${MB(m.rb)} js ${MB(m.js)}${pl}`);
    if (tick % 10 === 0) write();
    if (tick === 12) lines.push(`${now()} TOP ${(await page.evaluate(() => window.__mem.top(30)).catch(() => [])).join(' | ')}`);
    if (ready && (Date.now() - ready) / 1000 > Number(afterS)) {
      lines.push(`${now()} TOP ${(await page.evaluate(() => window.__mem.top(40)).catch(() => [])).join(' | ')}`);
      lines.push(`${now()} FORMATS ${Object.entries(m.formats).map(([k, v]) => `${isNaN(k) ? k : Number(k).toString(16)}:${MB(v)}`).join(' ')}`);
      lines.push(`${now()} END ready at ${((ready - t0) / 1000).toFixed(1)} s; peaks: wasm ${MB(m.wasmPeak)} gl ${MB(m.glPeak)} (tex ${MB(m.texPeak)} buf ${MB(m.bufPeak)}) renderer ${MB(peak.renderer)} gpu ${MB(peak['gpu-process'])}`);
      break;
    }
  }
  if (!ready) lines.push(`${now()} END never ready crashed=${crashed}`);
  write();
  await page.screenshot({ path: out.replace(/\.txt$/, '.png') }).catch(() => {});
  await ctx.close();
})();
