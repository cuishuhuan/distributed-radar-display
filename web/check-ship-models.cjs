const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const THREE = require('./three.min.js');
const html = fs.readFileSync(__dirname + '/ui-index.html', 'utf8');
for (const script of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) new vm.Script(script[1]);
const source = name => html.slice(html.indexOf('function ' + name + '('), html.indexOf('\nfunction ', html.indexOf('function ' + name + '(') + 1));
const shipKind = new Function(source('shipKind') + ';return shipKind')();
const shipModelFile = new Function('shipKind', source('shipModelFile') + ';return shipModelFile')(shipKind);
for (const [name, file] of [
  ['南沙邮轮24', 'ship-cruise-hq.glb'], ['远洋散货14', 'ship-bulk-hq.glb'],
  ['远海科考22', 'ship-research-hq.glb'], ['珠港拖轮17', 'ship-tug-hq.glb'],
  ['湾区集运13', 'ship-container-hq.glb'], ['海事巡逻16', 'ship-rescue-hq.glb'],
  ['粤海客轮15', 'ship-ferry-hq.glb'], ['南洋油轮18', 'ship-tanker-hq.glb'],
  ['珠江货轮02', 'cargo-ship-73k.glb'],
]) {
  assert.equal(shipModelFile({name}), file);
  const buffer = fs.readFileSync(__dirname + '/' + file);
  assert.equal(buffer.toString('ascii', 0, 4), 'glTF');
  assert.equal(buffer.readUInt32LE(8), buffer.length);
  const gltf = JSON.parse(buffer.subarray(20, 20 + buffer.readUInt32LE(12)));
  assert.ok(gltf.meshes.length);
  assert.ok(!(gltf.extensionsRequired || []).includes('KHR_draco_mesh_compression'));
}
const normalize = new Function('THREE', source('normalizeShipTemplate') + ';return normalizeShipTemplate')(THREE);
for (const [file, name] of [['ship-research-hq.glb', 'Ocean'], ['ship-cruise-hq.glb', 'Object_18'], ['ship-cruise-hq.glb', 'Object_19'], ['ship-cruise-hq.glb', 'Object_31']]) {
  const root = new THREE.Group(), background = new THREE.Group();
  background.name = name; root.add(background); normalize(root, file);
  assert.equal(root.children.length, 0);
}
const highlight = new Function('THREE', source('highlight3D') + ';return highlight3D')(THREE);
const model = new THREE.Group();
const material = new THREE.MeshStandardMaterial({emissive:0x173743, emissiveIntensity:.38});
model.add(new THREE.Mesh(new THREE.BoxGeometry(), material));
highlight(model, false, 0); highlight(model, true, 0); highlight(model, false, 0);
assert.equal(material.emissive.getHex(), 0x173743);
assert.equal(material.emissiveIntensity, .38);
console.log('9 ship assets, model selection, background removal and highlight restoration OK');
