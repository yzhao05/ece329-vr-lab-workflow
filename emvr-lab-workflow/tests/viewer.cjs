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
const assets = {"/":"index.html", "/stages.json":"stages.json", "/viewer.js":"viewer.js", "/style.css":"style.css"};
const mime = {"stages.json":"application/json","index.html":"text/html; charset=utf-8","style.css":"text/css","viewer.js":"text/javascript"};
const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost").pathname;
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
    assert.equal(await page.locator("main h1").innerText(), "Workflow progress");
    await page.locator("#language").click();
    assert.deepEqual(await page.locator("main h1, main h2").allTextContents(), ["当前流程","讲义依据","设计摘要","设计检查"]);
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
    view.builder = {current_gate:8, approved_gates:[0,1,2,3,4,5,6,8], accepted:false, stage:"acceptance_revalidation"};
    await page.waitForFunction(() => document.querySelector("#builder").textContent.includes("重新验收"));
    assert.match(await page.locator("#gates [aria-current=step]").innerText(), /Gate 6.*待重新验证/s);
    assert.match(await page.locator("#gates li").last().innerText(), /待开始/);
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

