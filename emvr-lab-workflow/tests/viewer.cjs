// Run with Node.js and Playwright installed. Start an isolated read-only HTTP fixture.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const { chromium } = require("playwright");
const web = path.join(__dirname, "../..", "web");
const view = {
  design_id: "design_a", revision: 1, flow: [{title:"实验想法完善", status:"进行中", steps:[{title:"课程映射",status:"进行中"}]}],
  builder: null, evidence: [{title:"磁场", pages:[113,120]}],
  notes:[{label:"实验想法", value:"通过电流观察中心磁场 <img src=x>"}],
  check: {details:{causal_chain:{cause:"current"},feasibility:{controls_are_defined:false}},status:"READY", final:false, issues:[], report_ready:false, builder_ready:false}
};
let latest = "design_a";
const words = new Uint32Array([1,3, 0,0,0, 0,0,0, 0,0,0, 1,3,3,0,1,2]);
new Float32Array(words.buffer,8,9).set([-1,0,0, 1,0,0, 0,1,0.5]);
let geometryRequests = 0;
const assets = {"/":"index.html", "/stages.json":"stages.json", "/viewer.js":"viewer.js", "/style.css":"style.css"};
const mime = {"stages.json":"application/json","index.html":"text/html; charset=utf-8","style.css":"text/css","viewer.js":"text/javascript"};
for (const asset of ["scene-preview.js","vendor/three-0.160.1/three.module.min.js","vendor/three-0.160.1/OrbitControls.js"]) {
  assets["/"+asset]=asset; mime[asset]="text/javascript";
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost").pathname;
  if (req.url === "/data/design_a.json?geometry=fixture") {
    geometryRequests++;
    if (geometryRequests === 1) { res.writeHead(503); return res.end(); }
    return res.end(Buffer.from(words.buffer));
  }
  if (url === "/data/latest.json" || url === "/data/design_a.json") {
    res.writeHead(200, {"Content-Type":"application/json"});
    return res.end(JSON.stringify(url.endsWith("latest.json") ? {design_id:latest} : view));
  }
  if (!Object.hasOwn(assets, url)) {res.writeHead(404); return res.end();}
  res.writeHead(200, {"Content-Type":mime[assets[url]]});
  res.end(fs.readFileSync(path.join(web, assets[url])));
});
(async () => {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  let browser;
  try {
    browser = await chromium.launch(process.env.CHROMIUM_CHANNEL ? {channel:process.env.CHROMIUM_CHANNEL} : {});
    const page = await browser.newPage({viewport:{width:1200,height:800}});
    const base = "http://127.0.0.1:" + server.address().port;
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector("#progress").textContent.includes("0 / 1"));
    assert.match(await page.locator(".substeps").innerText(), /Course mapping/);
    assert.match(await page.locator("#review-details").innerText(), /Causal chain/);
    assert.equal(await page.locator("html").getAttribute("lang"), "en");
    assert.equal(await page.locator("main h1:visible").innerText(), "Workflow progress");
    const toggle = page.locator("#layout-toggle");
    assert.equal(await toggle.isDisabled(), true);
    await page.locator("#language").click();
    assert.deepEqual(await page.locator("main h1:visible, main h2:visible").allTextContents(), ["当前流程","讲义依据","设计摘要","设计检查"]);
    assert.equal(await page.locator("input,textarea,[contenteditable],form,#notes img").count(), 0);
    assert.deepEqual(await page.locator(".flow h3").allTextContents(), ["Design · 实验设计","Builder · Unity 构建"]);
    assert.equal(await page.locator("#gates li").count(), 8);
    assert.match(await page.locator("#evidence").innerText(), /113–120/);
    let left = await page.locator(".flow").boundingBox();
    let right = await page.locator(".detail").boundingBox();
    assert.ok(right.x >= left.x + left.width);
    await page.setViewportSize({width:390,height:800});
    left = await page.locator(".flow").boundingBox();
    right = await page.locator(".detail").boundingBox();
    assert.ok(right.y >= left.y + left.height);
    view.builder = {current_gate:0,current_gate_name:"Boundary verified"};
    await page.waitForFunction(() => document.querySelector("#builder").textContent.includes("Gate 0"));
    view.builder = {current_gate:1,current_gate_name:"Brief confirmed",approved_gates:[0],gate_ready_for_approval:true};
    await page.waitForFunction(() => document.querySelector("#gates [aria-current=step]").textContent.includes("待确认"));
    assert.match(await page.locator("#gates li").first().innerText(), /已确认/);
    view.builder = {current_gate:8, approved_gates:[0,1,2,3,4,5,6,8], accepted:true, retrospective_pending:true};
    await page.waitForFunction(() => document.querySelector("#builder").textContent.includes("待归档复盘"));
    assert.match(await page.locator("#gates li").last().innerText(), /已确认/);
    view.builder = {current_gate:8, approved_gates:[0,1,2,3,4,5,6,8], accepted:true, upload_pending:true};
    await page.waitForFunction(() => document.querySelector("#builder").textContent.includes("上传副本待整理"));
    assert.match(await page.locator("#gates li").last().innerText(), /已确认/);
    view.builder = {current_gate:8, approved_gates:[0,1,2,3,4,5,6,8], accepted:false, stage:"acceptance_revalidation"};
    await page.waitForFunction(() => document.querySelector("#builder").textContent.includes("重新验收"));
    assert.match(await page.locator("#gates [aria-current=step]").innerText(), /Gate 6.*待重新验证/s);
    assert.match(await page.locator("#gates li").last().innerText(), /待开始/);
    const matrix = (x,y,z) => [1,0,0,0,0,1,0,0,0,0,1,0,x,y,z,1];
    view.layout = {scene:"Solenoid", source:"live", geometry:"fixture", objects:[
      {id:1,name:"Coil",position:[0,0,0],matrix:matrix(0,0,0),mesh:0,colors:["#eeaa00"]},
      {id:2,name:"Probe",position:[2,3,-4],matrix:matrix(2,3,-4),mesh:0,colors:["#006699"]}]};
    assert.equal(geometryRequests,0);
    await toggle.click();
    await page.waitForFunction(() => document.querySelector("#layout-map").hasAttribute("data-engine")
      && !document.querySelector("#layout-status").textContent);
    const canvas = page.locator("#layout-map");
    const rect = await canvas.boundingBox();
    const initial = await canvas.screenshot();
    await page.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);
    await page.mouse.down();
    await page.mouse.move(rect.x+rect.width/2+55,rect.y+rect.height/2+15,{steps:6});
    await page.mouse.up();
    const rotated = await canvas.screenshot();
    assert.ok(!rotated.equals(initial), "Orbit should change the rendered mesh");
    await page.mouse.wheel(0,-240);
    assert.ok(!(await canvas.screenshot()).equals(rotated), "Zoom should change the rendered mesh");
    assert.equal(await page.locator(".flow").isVisible(), false);
    await page.locator("#layout-object").selectOption("2");
    assert.match(await page.locator("#layout-position").innerText(), /X 2.*Y 3.*Z -4/);
    await page.locator("#language").click();
    assert.equal(await toggle.innerText(), "Workflow details");
    await toggle.click();
    assert.equal(await page.locator(".flow").isVisible(), true);
    await toggle.click();
    view.layout.objects[1].position[2] = -6;
    view.layout.objects[1].matrix[14] = -6;
    await page.waitForFunction(() => document.querySelector("#layout-position").textContent.includes("Z -6"));
    view.layout.objects = [];
    await page.waitForFunction(() => document.querySelector("#layout-toggle").disabled);
    assert.equal(await page.locator(".flow").isVisible(), true);
    assert.equal(geometryRequests,2, "Retry once after interrupted publication, then reuse the mesh on movement");
    await page.locator("#language").click();
    latest = "missing";
    await page.waitForFunction(() => document.querySelector("#progress").textContent.includes("无法读取"));
    assert.equal(await page.locator("#notes dt").count(), 0);
    assert.equal(await page.locator("#gates [aria-current]").count(), 0);
    latest = null;
    await page.waitForFunction(() => document.querySelector("#progress").textContent.includes("等待 Agent"));
    await page.locator("#language").click();
    await page.waitForFunction(() => document.querySelector("#gates").textContent.includes("Verify boundaries"));
    await page.locator("#language").click();
    latest = "design_a";
    await page.waitForFunction(() => document.querySelector("#notes dt") !== null);
    await page.goto(base + "/?design=missing");
    await page.waitForFunction(() => document.querySelector("#progress").textContent.includes("无法读取"));
    console.log("PASS: four panels, desktop/mobile, safe text, refresh, missing design.");
  } finally {
    if (browser) await browser.close();
    server.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

