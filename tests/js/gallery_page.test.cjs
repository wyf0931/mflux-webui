const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function setup({ stored = null, images = [] } = {}) {
  const factories = {};
  const store = new Map(stored ? [["mflux.galleryView", stored]] : []);
  const deleted = [];
  const context = {
    Alpine: { data: (name, factory) => { factories[name] = factory; }, start() {} },
    window: { setTimeout: () => 0, setInterval: () => 1, clearInterval: () => {}, location: { assign: () => {} } },
    navigator: { clipboard: { writeText: async () => {} } },
    localStorage: {
      getItem: (key) => store.get(key) ?? null,
      setItem: (key, value) => store.set(key, value),
      removeItem: (key) => store.delete(key),
    },
    confirm: () => true,
    File, FormData,
    URL: { createObjectURL: () => "blob:1", revokeObjectURL: () => {} },
    fetch: async (url, options) => {
      if (options?.method === "DELETE") {
        deleted.push(url);
        return { json: async () => ({ code: 0, data: null }) };
      }
      return { json: async () => ({ code: 0, data: images }) };
    },
  };
  const source = fs.readFileSync("mflux_webui/static/js/main.js", "utf8").replace('import Alpine from "alpinejs";', "");
  vm.runInNewContext(source, context);
  const page = factories.galleryPage();
  let opened = 0;
  let closed = 0;
  page.$refs = { previewDialog: { showModal() { opened++; }, close() { closed++; } } };
  return { page, store, deleted, openCount: () => opened, closeCount: () => closed };
}

const entry = { timestamp: "2026-10-22-10-30-00-000000", model: "mflux-community/qwen-image-2-1-turbo-mflux-q4", prompt: "一只猫", width: 768, height: 1376, duration: 12.5 };

test("默认使用网格视图，可从本地存储恢复表格视图", async () => {
  const grid = setup();
  await grid.page.init();
  assert.equal(grid.page.view, "grid");

  const table = setup({ stored: "table" });
  await table.page.init();
  assert.equal(table.page.view, "table");
});

test("切换视图会记住选择", async () => {
  const { page, store } = setup();
  await page.init();
  page.toggleView();
  assert.equal(page.view, "table");
  assert.equal(store.get("mflux.galleryView"), "table");
  page.toggleView();
  assert.equal(page.view, "grid");
  assert.equal(store.get("mflux.galleryView"), "grid");
});

test("点击行或小图打开大图预览", () => {
  const { page, openCount } = setup();
  page.openPreview(entry);
  assert.equal(page.preview.timestamp, entry.timestamp);
  assert.equal(openCount(), 1);
  page.openPreview(null);
  assert.equal(openCount(), 1, "空对象不应重复打开弹窗");
});

test("预览中删除会关闭弹窗并从列表移除", async () => {
  const { page, deleted, closeCount } = setup({ images: [entry] });
  await page.init();
  page.openPreview(entry);
  await page.remove(entry.timestamp);
  assert.equal(deleted.length, 1);
  assert.deepEqual(page.images, []);
  assert.equal(page.preview, null);
  assert.equal(closeCount(), 1);
});
