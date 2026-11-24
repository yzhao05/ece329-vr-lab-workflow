"use strict";
const find = id => document.getElementById(id);
const node = (tag, text) => {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
};
let language = "en";
try { language = localStorage.getItem("emvr-view-language") === "zh" ? "zh" : "en"; } catch {}
const t = (en, zh) => language === "en" ? en : zh;
const label = text => language === "en" ? (stages?.labels?.[text] || (typeof text === "string" ? text.replace(/^物体 (\d+)｜/, "Object $1 · ") : text)) : text;
const headings = [...document.querySelectorAll("[data-zh]")].map(el => [el, el.textContent]);
function localize() {
  document.documentElement.lang = language;
  for (const [el, en] of headings) el.textContent = t(en, el.dataset.zh);
  find("language").textContent = t("中文", "English");
  find("language").lang = t("zh", "en");
}
let previous = "";
let displayedId = null;
let standalone = null;
let refreshFailed = false;
let layout = null;
let layoutSignature = "";
let layoutOpen = false;
let layoutEndpoint = "";
let preview;
let loadedKey = "";
let loading = null;
let renderedLayout = null;
let previewState = "";

function previewStatus(state) {
  previewState = state;
  find("layout-status").textContent = state === "loading" ? t("Loading scene geometry…","正在读取场景模型…") :
    state === "retry" ? t("Waiting for the next geometry update…","等待下一次刷新重新读取模型…") :
    state === "error" ? t("Could not display the model. Check WebGL support and reopen the preview.","无法显示模型。请检查浏览器的 WebGL 支持，再重新打开预览。") : "";
}
function coordinates() {
  const selected = layout?.objects[find("layout-object").selectedIndex];
  find("layout-position").textContent = selected ? selected.position.map((n,i) =>
    "XYZ"[i] + " " + n.toLocaleString(language,{maximumFractionDigits:3})).join("   ·   ") + " m" : "";
}
async function displayModel() {
  const key = layoutEndpoint + "?geometry=" + layout.geometry;
  if (loading && loading.key !== key) {
    loading.controller.abort();
    loading = null;
  }
  if (loadedKey === key && renderedLayout === layout) return;
  if (loading?.key === key) return;
  const task = {key,controller:new AbortController()};
  loading = task;
  let fetchingGeometry = false;
  try {
    let buffer = null;
    if (loadedKey !== key) {
      previewStatus("loading");
      const module = await import("./scene-preview.js");
      if (loading !== task) return;
      fetchingGeometry = true;
      const response = await fetch(key,{signal:task.controller.signal});
      if (!response.ok) throw Error("Geometry unavailable");
      buffer = await response.arrayBuffer();
      fetchingGeometry = false;
      if (loading !== task || !layoutOpen) return;
      if (!preview) preview = module.createPreview(find("layout-map"),id => {
        find("layout-object").value = String(id);
        coordinates();
      });
    }
    preview.set(layout,buffer,layoutEndpoint);
    renderedLayout = layout;
    loadedKey = key;
    previewStatus("");
  } catch (err) {
    if (loading === task && err.name !== "AbortError") {
      preview?.reset();
      loadedKey = "";
      previewStatus(fetchingGeometry ? "retry" : "error");
    }
  } finally {
    if (loading === task) loading = null;
  }
}
function renderLayout() {
  const button = find("layout-toggle");
  button.disabled = !layout;
  button.textContent = layoutOpen ? t("Workflow details","工作流详情") : "Unity 3D";
  button.title = layout ? button.textContent : t("Available when this lab has exported 3D geometry","当前实验导出 3D 模型后可查看");
  button.setAttribute("aria-pressed", String(layoutOpen));
  document.querySelector(".flow").hidden = layoutOpen;
  document.querySelector(".detail").hidden = layoutOpen;
  find("scene-layout").hidden = !layoutOpen;
  if (layoutOpen) {
    find("layout-summary").textContent = [layout.scene, layout.source === "live" ? t("Live","实时") : t("Last saved","最近保存"),
      layout.objects.length + t(" objects"," 个物体")].join(" · ");
    coordinates();
    previewStatus(previewState);
    displayModel();
  } else {
    loading?.controller.abort();
    loading = null;
    previewStatus("");
  }
}

function updateLayout(next, endpoint = "") {
  next = next?.geometry && next.objects?.length ? next : null;
  const signature = next ? JSON.stringify(next) : "";
  if (signature === layoutSignature && endpoint === layoutEndpoint) {
    if (layoutOpen && previewState === "retry") displayModel();
    return;
  }
  if (!next || endpoint !== layoutEndpoint) {
    preview?.reset();
    renderedLayout = null;
    loadedKey = "";
  }
  layoutEndpoint = endpoint;
  layoutSignature = signature;
  const select = find("layout-object"), selected = select.value;
  layout = next;
  layoutOpen = Boolean(layout && layoutOpen);
  select.replaceChildren(...(layout?.objects || []).map(item => new Option(item.name,String(item.id))));
  if (layout?.objects.some(item => String(item.id) === selected)) select.value = selected;
  renderLayout();
}

find("layout-toggle").onclick = () => { layoutOpen = Boolean(layout && !layoutOpen); renderLayout(); };
find("layout-object").onchange = coordinates;
find("focus-object").onclick = () => preview?.fit(Number(find("layout-object").value));
find("fit-scene").onclick = () => preview?.fit();

function drawDetails(details = {}) {
  const target = find("review-details");
  target.replaceChildren();
  function section(en, zh, lines) {
    if (!lines.length) return;
    const pane = node("details", "");
    pane.open = true;
    pane.append(node("summary", t(en, zh)));
    const list = node("ul", "");
    for (const line of lines) list.append(node("li", line));
    pane.append(list);
    target.append(pane);
  }
  function fields(record, labels) {
    return labels.filter(([key]) => record?.[key] != null && record[key] !== "").map(([key, en, zh]) => {
      const value = record[key];
      return t(en, zh) + " · " + (typeof value === "boolean" ? (value ? t("Met", "已明确") : t("Pending", "待明确")) : label(value));
    });
  }
  section("Causal chain", "当前因果链", fields(details.causal_chain, [
    ["cause","Change","改变"],["response","Observe","观察"],["mechanism","Mechanism","依据"],["comparison","Compare","比较"]]));
  section("Feasibility", "概念可行性", fields(details.feasibility, [
    ["independent_variable_can_change","Adjustable variable","自变量可调整"],["observation_can_be_recorded","Recordable observation","观察量可记录"],
    ["comparison_is_defined","Defined comparison","比较条件已定义"],["controls_are_defined","Defined controls","控制条件已定义"],
    ["procedure_can_test_hypothesis","Procedure tests hypothesis","流程能够检验预期"],["course_link_is_defined","Defined course link","课程联系已定义"]]));
  section("Boundary cases", "边界情形", (details.boundary_cases || []).map(r => [r.case, r.relevance].filter(Boolean).join(" — ")));
  section("Option comparison", "方案比较", (details.option_comparison || []).map(r => [r.name, ...fields(r, [
    ["observability","Observability","可观察性"],["course_alignment","Course alignment","课程联系"],["controllability","Control","可控性"],
    ["vr_suitability","VR suitability","VR适配"],["recommendation","Recommendation","建议"]])].filter(Boolean).join(" · ")));
  section("Recent revisions", "最近修改", (details.versions || []).map(r => [r.id, r.reason, ...r.fields.map(label)].filter(Boolean).join(" · ")));
  section("Course traceability", "课程追溯", (details.traceability || []).map(r => [label(r.design_field_label),r.course_item,r.purpose].filter(Boolean).join(" — ")));
}
function draw(view) {
  const current = view.flow.find(step => step.status === "进行中");
  const done = view.flow.filter(step => step.status === "已确认").length;
  find("progress").textContent = (current ? label(current.title) : t("Design complete","设计已完成")) +
    t(" · Confirmed "," · 已确认 ") + done + " / " + view.flow.length;
  drawSteps(view.flow);
  drawBuilder(view.builder);
  find("evidence").replaceChildren(...(view.evidence.length ? view.evidence.map(ref =>
    node("li", ref.title + t(" · ECE329 lecture notes, pp. "," · ECE329 讲义 PDF 第 ") + ref.pages.join("–") + t("", " 页"))) :
    [node("li", t("No course evidence yet.","暂无已关联的讲义。"))]));
  find("notes").replaceChildren(...(view.notes.length ? view.notes.flatMap(note =>
    [node("dt", label(note.label)), node("dd", note.value)]) : [node("dd", t("No design notes yet.","暂无设计内容。"))]));
  const check = view.check;
  find("checks").textContent = check.archived ? t("Archived design. Builder handoff requires a confirmed VR design.","历史设计已归档。Builder 交接需使用已确认的 VR 方案。") :
    [check.final ? t("Final review","整份方案检查") : t("Stage review","当前阶段检查"),
     check.issues.length ? t("Items to review","有待核对事项") : check.status === "READY" ? t("No open issues","本次未发现待处理项") : t("Pending","等待检查"),
     t("Design PDF","设计 PDF") + " · " + label(check.report_ready ? "可导出" : "待完成"),
     t("Builder input PDF","Builder 输入 PDF") + " · " + label(check.builder_ready ? "可导出" : "待完成")].join(" | ");
  find("issues").replaceChildren(...check.issues.map(i => node("li", [i.finding, i.suggestion].filter(Boolean).join(" "))));
  drawDetails(check.details);
}
const params = new URLSearchParams(location.search);
const requested = params.get("design");
const session = params.get("session");
let stages;
let lastStatus = "";

function row(title, status, active) {
  const item = node("li", label(title));
  if (active) item.setAttribute("aria-current", "step");
  item.append(node("small", label(status)));
  return item;
}
function drawSteps(steps) {
  find("steps").replaceChildren(...steps.map(s => {
    const item = row(s.title, s.status, s.status === "进行中");
    if (s.steps?.length) {
      const list = node("ol", "");
      list.className = "substeps";
      list.append(...s.steps.map(step => row(step.title, step.status, step.status === "进行中")));
      item.append(list);
    }
    return item;
  }));
}
function drawBuilder(b) {
  const recheck = b?.stage === "acceptance_revalidation" ? 6 :
    b?.stage === "handbooks_revalidation" ? 8 : null;
  const current = recheck ?? b?.current_gate;
  const approved = Array.isArray(b?.approved_gates) ? new Set(b.approved_gates) : null;
  find("builder").textContent = !b ? t("Waiting for a Builder workspace","等待构建工作区") :
    b.migration_required ? t("Legacy Builder workspace requires migration", "旧版 Builder 工作区需要迁移") :
    recheck === 6 ? t("Gate 6 · Scene acceptance must be renewed", "Gate 6 · 场景需要重新验收") :
    recheck === 8 ? t("Gate 8 · Handbooks require revalidation", "Gate 8 · 手册需要重新验证") :
    b.retrospective_pending ? t("Gate 8 · Accepted, retrospective pending", "Gate 8 · 验收通过，待归档复盘") :
    b.upload_pending ? t("Gate 8 · Accepted, upload folders pending", "Gate 8 · 验收通过，上传副本待整理") :
    b.workflow_complete ? t("Build complete","构建已完成") : current == null ? t("Check Builder status","需要核对 Builder 状态") :
    "Gate " + current + " · " + label(stages.builder.find(g => g.gate === current)?.title || b.current_gate_name || "") + (b.accepted ? t(" · Scene accepted"," · 场景已验收") : "");
  find("gates").replaceChildren(...stages.builder.map(g => {
    const active = current === g.gate && !b.workflow_complete && !b.retrospective_pending && !b.upload_pending;
    const invalidated = recheck !== null && g.gate >= recheck;
    const status = active && invalidated ? t("Needs revalidation", "待重新验证") : active ? (b.gate_ready_for_approval ? "待确认" : "进行中") :
      !invalidated && (b?.workflow_complete || (approved ? approved.has(g.gate) : current != null && g.gate < current)) ? "已确认" : "待开始";
    return row("Gate " + g.gate + " · " + label(g.title), status, active);
  }));
}
function emptySteps(status) {
  return stages.design.map((title, i) => ({title, status, steps: i ? [] :
    (stages.idea_steps || []).map(title => ({title, status}))}));
}
function clearDesign() {
  displayedId = null;
  previous = "";
  drawSteps(emptySteps("待开始"));
  drawBuilder(null);
  find("evidence").replaceChildren(node("li", t("No course evidence yet.","暂无已关联的讲义。")));
  find("notes").replaceChildren(node("dd", t("No design notes yet.","暂无设计内容。")));
  find("checks").textContent = t("Waiting for a design.","等待设计记录。");
  find("issues").replaceChildren();
  drawDetails();
}
async function read(path) {
  const response = await fetch(path, {cache:"no-store"});
  if (!response.ok) throw Error(String(response.status));
  return response.json();
}
function errorStatus() {
  return previous ? t("Refresh interrupted. Showing the last update.","更新暂时中断，显示最近一次进度。") :
    t("Could not read this design.","无法读取该设计的进度。");
}
async function refresh() {
  try {
    if (!stages) {
      stages = await read("stages.json");
      drawSteps(emptySteps("待开始"));
      drawBuilder(null);
    }
    const target = session ? await read("_session/" + encodeURIComponent(session)) : null;
    standalone = target?.standalone ? target : null;
    if (standalone) {
      updateLayout(target.layout,"_session/" + encodeURIComponent(session));
      drawSteps(emptySteps("未关联设计"));
      drawBuilder(target.builder);
      lastStatus = t("Standalone Builder workspace","独立 Builder 工作区");
    } else {
      let id = target ? target.design_id : requested;
      if (!target && requested === null) {
        try { id = (await read("data/latest.json")).design_id; }
        catch (err) { if (err.message !== "404") throw err; }
      }
      if (id == null) {
        updateLayout(null);
        if (displayedId) clearDesign();
        lastStatus = t("Waiting for the agent to create a design.","等待 Agent 创建设计。");
      } else {
        if (displayedId && displayedId !== id) { updateLayout(null); clearDesign(); }
        if (!/^[A-Za-z0-9_-]{1,80}$/.test(id)) throw Error("invalid");
        const view = await read("data/" + id + ".json");
        if (view.design_id !== id) throw Error("mismatch");
        updateLayout(view.layout,"data/" + id + ".json");
        delete view.layout;
        const serial = JSON.stringify(view);
        if (previous !== serial) {
          draw(view);
          displayedId = id;
          previous = serial;
          lastStatus = find("progress").textContent;
        }
      }
    }
    refreshFailed = false;
    find("progress").textContent = lastStatus;
  } catch {
    updateLayout(null);
    refreshFailed = true;
    find("progress").textContent = errorStatus();
  } finally {
    setTimeout(refresh, 2500);
  }
}
refresh();

localize();
renderLayout();
find("language").onclick = () => {
  language = t("zh", "en");
  try { localStorage.setItem("emvr-view-language", language); } catch {}
  localize();
  renderLayout();
  if (previous) { draw(JSON.parse(previous)); lastStatus = find("progress").textContent; }
  else if (stages) {
    clearDesign();
    if (standalone) {
      drawSteps(emptySteps("未关联设计"));
      drawBuilder(standalone.builder);
    }
    lastStatus = standalone ? t("Standalone Builder workspace","独立 Builder 工作区") :
      t("Waiting for the agent to create a design.","等待 Agent 创建设计。");
    find("progress").textContent = lastStatus;
  }
  if (refreshFailed) find("progress").textContent = errorStatus();
};
