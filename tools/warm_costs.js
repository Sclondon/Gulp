// node tools/warm_costs.js <log from chrome_load.js> [n]: what each warm-up step cost, the n dearest first
// (a GULP WARM line's +ms is what the step BEFORE it took: its two frames, compiles and all)
const fs = require('fs');
const lines = fs.readFileSync(process.argv[2], 'utf8').split('\n');
const steps = [];
let start = null, ready = null, warmAt = null;
for (const l of lines) {
  const m = l.match(/^([\d.]+) log GULP WARM (\d+) ms \+(\d+) (\d+)\/(\d+) x(\d+)( lamp)?( air)? (.*)$/);
  if (m) steps.push({ t: +m[1], ms: +m[2], took: +m[3], n: +m[6], lamp: !!m[7], air: !!m[8], names: m[9] });
  if (/GULP WARM \d+ things/.test(l)) warmAt = parseFloat(l);
  if (/everything is ready/.test(l)) ready = l;
}
const cost = [];
for (let i = 0; i + 1 < steps.length; i++) cost.push({ ...steps[i], cost: steps[i + 1].took });
const sum = (a) => a.reduce((s, x) => s + x.cost, 0);
const kind = (s) => s.air ? 'air' : s.lamp ? 'lamp' : (/\.gdshader|::|grass|@/.test(s.names) ? 'material' : 'kind');
const groups = {};
for (const c of cost) { const k = kind(c); groups[k] = groups[k] || { steps: 0, items: 0, ms: 0, frames: 0 }; groups[k].steps++; groups[k].items += c.n; groups[k].ms += c.cost; }
console.log('warm list printed at', warmAt, 's;', ready);
console.log('first step logged at', steps[0] && steps[0].t, 's (ms into warming', steps[0] && steps[0].ms, ')');
console.log(groups);
const fast = cost.filter((c) => c.cost < 60).length;
console.log('steps', cost.length, 'under 60 ms', fast, 'ms in steps under 60:', sum(cost.filter((c) => c.cost < 60)), 'ms in 60..300:', sum(cost.filter((c) => c.cost >= 60 && c.cost < 300)), 'ms over 300:', sum(cost.filter((c) => c.cost >= 300)));
cost.sort((a, b) => b.cost - a.cost);
for (const c of cost.slice(0, Number(process.argv[3] || 25))) console.log(c.cost, 'x' + c.n, c.lamp ? 'lamp' : '', c.air ? 'air' : '', c.names.slice(0, 140));
