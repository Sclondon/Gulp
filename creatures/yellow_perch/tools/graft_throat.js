// node graft_throat.js <kept.glb> <built.glb> <out.glb>
//
// Takes the throat-and-gills surface (the second primitive) of a model just built by build_yellow_perch.py and
// puts it beside the single surface of an older export of the same model, which is kept byte for byte. Why: the
// yellow perch's full and low models in models/ were exported before the build script drew the jaw's tip flat
// (and by a version of it that cannot now be run again), so a rebuild of them comes out a few points different;
// grafting keeps them exactly as they were and adds the gills (2026-11-18). Node 20, no packages.
const fs = require("fs");

function read(path) {
	const b = fs.readFileSync(path);
	const jsonLength = b.readUInt32LE(12);
	const json = JSON.parse(b.slice(20, 20 + jsonLength).toString());
	const binLength = b.readUInt32LE(20 + jsonLength);
	return { json, bin: b.slice(28 + jsonLength, 28 + jsonLength + binLength) };
}

function pad(buffer, by, fill) {
	const extra = (by - (buffer.length % by)) % by;
	return Buffer.concat([buffer, Buffer.alloc(extra, fill)]);
}

const [keptPath, builtPath, outPath] = process.argv.slice(2);
const kept = read(keptPath);
const built = read(builtPath);
if (kept.json.meshes[0].primitives.length !== 1 || built.json.meshes[0].primitives.length !== 2) {
	throw new Error("expected one surface in the kept model and two in the built one");
}
const second = JSON.parse(JSON.stringify(built.json.meshes[0].primitives[1]));
let bin = pad(kept.bin, 4, 0);
const accessorFor = {};
for (const index of [...Object.values(second.attributes), second.indices]) {
	if (accessorFor[index] !== undefined) {
		continue;
	}
	const accessor = JSON.parse(JSON.stringify(built.json.accessors[index]));
	const view = built.json.bufferViews[accessor.bufferView];
	const data = built.bin.slice(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength);
	const newView = Object.assign({}, view, { buffer: 0, byteOffset: bin.length });
	bin = pad(Buffer.concat([bin, data]), 4, 0);
	kept.json.bufferViews.push(newView);
	accessor.bufferView = kept.json.bufferViews.length - 1;
	kept.json.accessors.push(accessor);
	accessorFor[index] = kept.json.accessors.length - 1;
}
for (const key of Object.keys(second.attributes)) {
	second.attributes[key] = accessorFor[second.attributes[key]];
}
second.indices = accessorFor[second.indices];
kept.json.materials.push(built.json.materials[second.material]);
second.material = kept.json.materials.length - 1;
kept.json.meshes[0].primitives.push(second);
kept.json.buffers[0].byteLength = bin.length;
const json = pad(Buffer.from(JSON.stringify(kept.json)), 4, 0x20);
const header = Buffer.alloc(12);
header.writeUInt32LE(0x46546c67, 0);
header.writeUInt32LE(2, 4);
header.writeUInt32LE(12 + 8 + json.length + 8 + bin.length, 8);
const jsonHead = Buffer.alloc(8);
jsonHead.writeUInt32LE(json.length, 0);
jsonHead.writeUInt32LE(0x4e4f534a, 4);
const binHead = Buffer.alloc(8);
binHead.writeUInt32LE(bin.length, 0);
binHead.writeUInt32LE(0x004e4942, 4);
fs.writeFileSync(outPath, Buffer.concat([header, jsonHead, json, binHead, bin]));
console.log("GRAFTED " + outPath + ": the kept surface and " + kept.json.accessors[second.indices].count / 3 + " triangles of throat and gills");
