const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function setup(models = [], reuse = null) {
  const factories = {};
  const revoked = [];
  const stored = new Map(reuse ? [["mflux.reuseGeneration", JSON.stringify(reuse)]] : []);
  const context = {
    Alpine: { data: (name, factory) => { factories[name] = factory; }, start() {} },
    window: {}, navigator: {}, File,
    URL: { createObjectURL: () => `blob:${Math.random()}`, revokeObjectURL: (url) => revoked.push(url) },
    localStorage: { getItem: (key) => stored.get(key), removeItem: (key) => stored.delete(key) },
    fetch: async () => ({ json: async () => ({ code: 0, data: models }) }),
  };
  const source = fs.readFileSync("mflux_webui/static/js/main.js", "utf8").replace('import Alpine from "alpinejs";', "");
  vm.runInNewContext(source, context);
  const page = factories.generationPage();
  page.$refs = { image: { value: "" } };
  return { page, revoked, queue: factories.queuePage() };
}

test("粘贴图片后自动关联附件、展开预览，替换和移除时释放预览 URL", () => {
  const { page, revoked } = setup();
  const png = new File(["png bytes"], "screenshot.png", { type: "image/png" });
  let prevented = false;
  page.pasteImage({ clipboardData: { items: [{ kind: "file", type: png.type, getAsFile: () => png }] }, preventDefault() { prevented = true; } });
  assert.ok(prevented);
  assert.equal(page.referenceFile.type, "image/png");
  assert.match(page.referenceFile.name, /^clipboard-\d+\.png$/);
  assert.equal(page.referenceFile.size, png.size);
  assert.ok(page.showAdvanced);
  const oldPreview = page.imagePreview;
  page.setReferenceImage(png);
  assert.equal(revoked[0], oldPreview);
  page.removeReferenceImage();
  assert.equal(page.referenceFile, null);
  assert.equal(page.imagePreview, "");
  assert.equal(revoked.length, 2);
});

test("普通文本粘贴保持默认行为，不影响参考图", () => {
  const { page } = setup();
  page.form.prompt = "已有提示词";
  page.pasteImage({ clipboardData: { items: [{ kind: "string", type: "text/plain" }] }, preventDefault() { assert.fail("不应拦截文字粘贴"); } });
  assert.equal(page.form.prompt, "已有提示词");
  assert.equal(page.referenceFile, null);
});

test("Qwen 多图按添加顺序编号，插入引用并在切换单图时释放额外预览", () => {
  const { page, revoked } = setup();
  page.models = [{ repoId: "qwen", family: "Qwen Image 2.1 Turbo" }];
  page.form.modelId = "qwen";
  page.form.generationMode = "reference";
  const one = new File(["one"], "one.png", { type: "image/png" });
  const two = new File(["two"], "two.png", { type: "image/png" });
  page.chooseImage({ target: { files: [one, two], value: "files" } });
  assert.equal(page.referenceImages.length, 2);
  assert.equal(page.referenceImages[1].file, two);
  page.insertReference(1);
  assert.match(page.form.prompt, /<image2>/);
  page.form.generationMode = "img2img";
  page.changeGenerationMode();
  assert.equal(page.referenceImages.length, 1);
  assert.equal(page.referenceFile, one);
  assert.equal(revoked.length, 1);
  page.removeReferenceImage();
  assert.equal(page.referenceImages.length, 0);
  assert.equal(revoked.length, 2);
});

test("Qwen 多图上限为 10，移除单张后顺序保持且可继续添加", () => {
  const { page } = setup();
  page.models = [{ repoId: "qwen", family: "Qwen Image 2.1 Turbo" }];
  page.form.modelId = "qwen";
  page.form.generationMode = "reference";
  for (let i = 0; i < 11; i++) page.setReferenceImage(new File([String(i)], `${i}.png`, { type: "image/png" }));
  assert.equal(page.referenceImages.length, 10);
  assert.match(page.error, /最多/);
  page.removeReferenceImage(0);
  assert.equal(page.referenceFile.name, "1.png");
  page.setReferenceImage(new File(["new"], "new.png", { type: "image/png" }));
  assert.equal(page.referenceImages.length, 10);
  assert.equal(page.referenceImages[9].file.name, "new.png");
});

test("历史多图参数复用恢复编辑模式，并提示按原顺序重新上传", async () => {
  const models = [{ repoId: "qwen", family: "Qwen Image 2.1 Turbo", steps: 8, guidanceMode: "fixed", guidance: 1, installed: true }];
  const { page } = setup(models, { modelId: "qwen", prompt: "图一参考图二", generationMode: "reference", hasReference: true });
  await page.init();
  assert.equal(page.referenceEditing, true);
  assert.equal(page.referenceImages.length, 0);
  assert.match(page.reuseNotice, /原顺序/);
});

test("不支持的图片类型不会替换已有参考图", () => {
  const { page } = setup();
  const png = new File(["png"], "local.png", { type: "image/png" });
  page.setReferenceImage(png);
  page.setReferenceImage(new File(["gif"], "bad.gif", { type: "image/gif" }), true);
  assert.equal(page.referenceFile, png);
  assert.match(page.error, /仅支持/);
});

test("模型切换恢复步数和引导设置，历史复用保留种子 0 并修正 Turbo CFG", async () => {
  const models = [
    { repoId: "qwen", family: "Qwen Image 2.1 Turbo", installed: true, steps: 8, guidance: 1, guidanceMode: "fixed" },
    { repoId: "zimage", installed: true, steps: 4, guidance: null, guidanceMode: "ignored" },
    { repoId: "krea", installed: true, steps: 8, guidance: 1, guidanceMode: "editable" },
  ];
  const { page } = setup(models, { modelId: "qwen", steps: 16, guidance: 7, seed: 0 });
  await page.init();
  assert.equal(page.form.steps, 16);
  assert.equal(page.form.seed, 0);
  assert.equal(page.form.guidance, 1);
  assert.equal(page.guidanceEditable, false);
  page.form.modelId = "zimage"; page.changeModel();
  assert.equal(page.form.steps, 4);
  assert.equal(page.form.guidance, "");
  page.form.modelId = "krea"; page.changeModel();
  assert.equal(page.form.steps, 8);
  assert.equal(page.guidanceEditable, true);
});

test("日志弹窗按需读取完整堆栈，关闭后忽略迟到的响应", async () => {
  const { queue } = setup({ logs: "Traceback\n完整堆栈\nRuntimeError: broken" });
  let opened = 0;
  queue.$refs = { logDialog: { showModal() { opened++; } } };
  await queue.openLogs({ taskId: "failed-1", error: "错误摘要" });
  assert.equal(opened, 1);
  assert.match(queue.logText, /完整堆栈/);
  const request = queue.openLogs({ taskId: "failed-2", error: "另一个摘要" });
  queue.logTask = null;
  await request;
  assert.equal(queue.logText, "另一个摘要");
});
