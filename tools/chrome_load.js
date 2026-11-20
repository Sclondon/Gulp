// Loads a Gulp web build in the real Chrome (playwright-core, ANGLE D3D11 on the GPU) and logs its console lines
// with seconds since the page was opened, until "everything is ready" (tools/PERF.md, "Real Chrome").
//   node tools/serve_web.js <folder holding the export> 8741        (a static server, no caching)
//   node tools/chrome_load.js http://127.0.0.1:8741/index.html <profile folder> <out.txt> [headless 0|1] [timeout s]
//   node tools/warm_costs.js <out.txt> [how many]                    (what each warm-up step cost)
// A new profile folder is a first visit (cold GPU cache); the same folder again is a second visit.
// EXTRA="--flag ..." adds Chrome flags.
const { chromium } = require('C:/Projects/scareathon/trailer/node_modules/playwright-core');
const fs = require('fs');
(async () => {
  const [url, profile, out, headless = '1', timeoutS = '600'] = process.argv.slice(2);
  const ctx = await chromium.launchPersistentContext(profile, {
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: headless === '1',
    viewport: { width: 1280, height: 720 },
    args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--mute-audio', '--autoplay-policy=no-user-gesture-required', ...(process.env.EXTRA ? process.env.EXTRA.split(' ') : [])],
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  const t0 = Date.now();
  const lines = [];
  let ready = false;
  const write = () => fs.writeFileSync(out, lines.join('\n') + '\n');
  page.on('console', (m) => {
    const s = `${((Date.now() - t0) / 1000).toFixed(2)} ${m.type()} ${m.text()}`;
    lines.push(s);
    if (/everything is ready|GULP READY/.test(m.text())) ready = true;
    if (lines.length % 20 === 0) write();
  });
  page.on('pageerror', (e) => lines.push(`${((Date.now() - t0) / 1000).toFixed(2)} PAGEERROR ${e}`));
  await page.goto(url);
  const gl = await page.evaluate(() => {
    const c = document.createElement('canvas').getContext('webgl2');
    const e = c.getExtension('WEBGL_debug_renderer_info');
    return c.getParameter(e.UNMASKED_RENDERER_WEBGL);
  });
  lines.push(`0 info RENDERER ${gl}`);
  let frames = 0;
  await page.evaluate(() => { window.__f = 0; (function f() { window.__f++; requestAnimationFrame(f); })(); });
  while (!ready && (Date.now() - t0) / 1000 < Number(timeoutS)) {
    await new Promise((r) => setTimeout(r, 1000));
    const f = await page.evaluate(() => window.__f).catch(() => -1);
    if (Math.round((Date.now() - t0) / 1000) % 10 === 0) lines.push(`${((Date.now() - t0) / 1000).toFixed(2)} info FRAMES ${f}`);
    frames = f;
  }
  await new Promise((r) => setTimeout(r, 4000));
  lines.push(`${((Date.now() - t0) / 1000).toFixed(2)} info END ready=${ready} frames=${frames}`);
  write();
  await page.screenshot({ path: out.replace(/\.txt$/, '.png') }).catch(() => {});
  await ctx.close();
})();

