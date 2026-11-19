import * as THREE from "three";
import {OrbitControls} from "./vendor/three-0.160.1/OrbitControls.js";

// Little-endian buffers from WriteGeometry: one shared vertex array per mesh,
// with independent index ranges for each Unity submesh / material slot.
function unpack(buffer) {
  let offset = 0;
  const words = new Uint32Array(buffer);
  function integer() {
    if (offset >= words.length) throw Error("Incomplete geometry");
    return words[offset++];
  }
  function array(Type, count) {
    if (count > words.length-offset) throw Error("Incomplete mesh");
    const result = new Type(buffer,offset*4,count);
    offset += count;
    return result;
  }
  const meshCount = integer(), meshes = [];
  for (let m=0; m<meshCount; m++) {
    const vertices = new THREE.BufferAttribute(array(Float32Array,integer()*3),3);
    const parts = [], count = integer();
    for (let i=0; i<count; i++) {
      const topology = integer(), indices = array(Uint32Array,integer());
      if (!indices.length) continue;
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position",vertices);
      geometry.setIndex(new THREE.BufferAttribute(indices,1));
      if (topology === 3) geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      parts.push({geometry, lines:topology===2, slot:i});
    }
    meshes.push(parts);
  }
  if (offset !== words.length) throw Error("Unexpected geometry data");
  return meshes;
}

export function createPreview(canvas, onSelect) {
  const renderer = new THREE.WebGLRenderer({canvas,antialias:true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1,2));
  renderer.setClearColor(0xeaf1ef);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff,0xa6aaa2,1.9));
  const sun = new THREE.DirectionalLight(0xffffff,2.2);
  sun.position.set(3,6,4);
  scene.add(sun);
  const root = new THREE.Group();
  root.scale.z = -1; // Unity is left-handed with +Z forward.
  scene.add(root);
  const camera = new THREE.PerspectiveCamera(42,1,0.01,2000);
  const controls = new OrbitControls(camera,canvas);
  const draw = () => renderer.render(scene,camera);
  controls.addEventListener("change",draw);
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w,h,false);
    camera.aspect = w/h;
    camera.updateProjectionMatrix();
    draw();
  }
  new ResizeObserver(resize).observe(canvas);
  const materials = new Map();
  let meshes = [], digest = "", scope = "", instances = new Map();

  function fit(id) {
    const target = instances.get(id) || root;
    const box = new THREE.Box3().setFromObject(target);
    if (box.isEmpty()) return;
    const {center,radius} = box.getBoundingSphere(new THREE.Sphere());
    const halfAngle = THREE.MathUtils.degToRad(camera.fov/2);
    const distance = Math.max(0.005,radius) * 1.12 /
      Math.sin(Math.min(halfAngle,Math.atan(Math.tan(halfAngle)*camera.aspect)));
    camera.near = Math.max(0.00001,distance/10000);
    camera.far = Math.max(distance*100,new THREE.Box3().setFromObject(root).getSize(new THREE.Vector3()).length()*4);
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    camera.position.copy(center).addScaledVector(new THREE.Vector3(1,.7,1.25).normalize(),distance);
    controls.update();
    draw();
  }

  function clearInstances() {
    root.clear();
    instances.clear();
    for (const mat of materials.values()) mat.dispose();
    materials.clear();
  }
  function reset() {
    clearInstances();
    for (const parts of meshes) for (const part of parts) part.geometry.dispose();
    meshes = [];
    digest = scope = "";
    draw();
  }
  function set(layout, buffer, workspace) {
    const first = scope !== workspace || !instances.size;
    if (digest !== layout.geometry) {
      reset();
      meshes = unpack(buffer);
      digest = layout.geometry;
    }
    scope = workspace;
    const removed = new Set(instances.keys());
    for (const item of layout.objects) {
      removed.delete(item.id);
      const appearance = [item.mesh,...item.colors].join("|");
      const existing = instances.get(item.id);
      if (existing?.userData.appearance === appearance) {
        existing.matrix.fromArray(item.matrix);
        existing.matrixWorldNeedsUpdate = true;
        continue;
      }
      if (existing) root.remove(existing);
      const group = new THREE.Group();
      group.userData.appearance = appearance;
      group.matrixAutoUpdate = false;
      group.matrix.fromArray(item.matrix);
      for (const part of meshes[item.mesh]) {
        const color = item.colors[part.slot] || "#9ba8a7";
        const key = part.lines + color;
        if (!materials.has(key)) materials.set(key,part.lines ? new THREE.LineBasicMaterial({color}) :
          new THREE.MeshStandardMaterial({color,side:THREE.DoubleSide,roughness:.78}));
        const obj = part.lines ? new THREE.LineSegments(part.geometry,materials.get(key)) :
          new THREE.Mesh(part.geometry,materials.get(key));
        obj.userData.id = item.id;
        group.add(obj);
      }
      root.add(group);
      instances.set(item.id,group);
    }
    for (const id of removed) {
      root.remove(instances.get(id));
      instances.delete(id);
    }
    const used = new Set();
    for (const group of instances.values()) for (const part of group.children) used.add(part.material);
    for (const [key,material] of materials) if (!used.has(material)) {
      material.dispose();
      materials.delete(key);
    }
    root.updateWorldMatrix(true,true);
    resize();
    if (first) fit();
    else draw();
  }
  let start;
  canvas.addEventListener("pointerdown",e => { start = [e.clientX,e.clientY]; });
  canvas.addEventListener("pointerup",e => {
    if (!start || e.button !== 0 || Math.hypot(start[0]-e.clientX,start[1]-e.clientY)>4) return;
    const rect = canvas.getBoundingClientRect(), ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(2*(e.clientX-rect.left)/rect.width-1,1-2*(e.clientY-rect.top)/rect.height),camera);
    const hit = ray.intersectObjects(root.children,true)[0];
    if (hit) onSelect(hit.object.userData.id);
  });
  return {set,fit,reset};
}
