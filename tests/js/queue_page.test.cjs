const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function setup() {
  const factories = {};
  const context = {
    Alpine: { data: (name, factory) => { factories[name] = factory; }, start() {} },
    window: { setTimeout: () => 0, setInterval: () => 1, clearInterval: () => {} },
    navigator: { clipboard: { writeText: async () => {} } },
    File, FormData,
    URL: { createObjectURL: () => "blob:1", revokeObjectURL: () => {} },
    localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
    document: { documentElement: { dataset: {} }, body: {} },
    fetch: async () => ({ json: async () => ({ code: 0, data: { tasks: [], queueLength: 0, runningTaskId: null } }) }),
  };
  const source = fs.readFileSync("mflux_webui/static/js/main.js", "utf8").replace('import Alpine from "alpinejs";', "");
  vm.runInNewContext(source, context);
  const page = factories.queuePage();
  let opened = 0;
  page.$refs = { detailDialog: { showModal() { opened++; }, close() {} }, logDialog: { showModal() {}, close() {} } };
  return { page, openCount: () => opened };
}

test("点击行会打开任务详情弹窗并保存当前任务", () => {
  const { page, openCount } = setup();
  const task = { taskId: "t-1", status: "succeeded", prompt: "一只红色的猫", width: 768, height: 1376 };
  page.openDetail(task);
  assert.equal(page.detailTask.taskId, "t-1");
  assert.equal(openCount(), 1);
});

test("详情里的参数摘要包含步数、引导与种子", () => {
  const { page } = setup();
  page.detailTask = { steps: 8, metadata: { guidance: 1.5, seed: 0 } };
  assert.equal(page.paramSummary, "8 步 · 引导 1.5 · 种子 0");
  page.detailTask = { steps: null, metadata: {} };
  assert.equal(page.paramSummary, "默认 步");
});

test("详情里的生成方式按模式与参考图数量区分", () => {
  const { page } = setup();
  page.detailTask = { generationMode: "reference", referenceCount: 2 };
  assert.equal(page.modeLabel, "多参考图编辑");
  page.detailTask = { generationMode: "img2img", referenceCount: 1 };
  assert.equal(page.modeLabel, "保持构图（单图）");
  page.detailTask = { generationMode: "img2img", referenceCount: 0 };
  assert.equal(page.modeLabel, "文生图");
});
