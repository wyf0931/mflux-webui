const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function setup({ describeResponse = null, model = { modelId: "lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit", cached: true } } = {}) {
  const factories = {};
  const revoked = [];
  const clipboard = [];
  const stored = new Map();
  const context = {
    Alpine: { data: (name, factory) => { factories[name] = factory; }, start() {} },
    window: {
      setTimeout: (callback) => { callback(); return 0; },
      setInterval: () => 1,
      clearInterval: () => {},
      location: { assign: (url) => stored.set("mflux.navigated", url) },
    },
    navigator: { clipboard: { writeText: async (text) => clipboard.push(text) } },
    File, FormData,
    URL: { createObjectURL: () => `blob:${Math.random()}`, revokeObjectURL: (url) => revoked.push(url) },
    localStorage: {
      getItem: (key) => stored.get(key) ?? null,
      setItem: (key, value) => stored.set(key, value),
    },
    fetch: async (url) => ({
      json: async () => (String(url).includes("/api/describe/model")
        ? { code: 0, data: model }
        : describeResponse || { code: 0, data: null }),
    }),
  };
  const source = fs.readFileSync("mflux_webui/static/js/main.js", "utf8").replace('import Alpine from "alpinejs";', "");
  vm.runInNewContext(source, context);
  const page = factories.describePage();
  page.$refs = { file: { value: "" } };
  return { page, revoked, clipboard, stored };
}

const png = () => new File(["png bytes"], "photo.png", { type: "image/png" });

test("粘贴图片后生成预览，替换与移除时释放旧的预览 URL", () => {
  const { page, revoked } = setup();
  let prevented = false;
  page.pasteImage({
    clipboardData: { items: [{ kind: "file", type: "image/png", getAsFile: () => png() }] },
    preventDefault() { prevented = true; },
  });
  assert.ok(prevented);
  assert.equal(page.image.name, "剪贴板图片");
  assert.equal(page.image.file.type, "image/png");
  const firstPreview = page.image.preview;
  page.setImage(png());
  assert.equal(revoked[0], firstPreview);
  assert.equal(page.image.name, "photo.png");
  const secondPreview = page.image.preview;
  page.removeImage();
  assert.equal(revoked[1], secondPreview);
  assert.equal(page.image, null);
});

test("拖拽与文件选择都接受图片，非图片内容给出错误提示", () => {
  const { page } = setup();
  page.dropImage({ dataTransfer: { files: [png()] } });
  assert.equal(page.image.name, "photo.png");
  assert.equal(page.dragging, false);
  page.chooseImage({ target: { files: [png()], value: "files" } });
  assert.equal(page.image.name, "photo.png");
  page.dropImage({ dataTransfer: { files: [new File(["x"], "a.txt", { type: "text/plain" })] } });
  assert.match(page.error, /不是图片/);
  page.setImage(new File(["gif"], "a.gif", { type: "image/gif" }));
  assert.match(page.error, /仅支持/);
});

test("描述成功后返回提示词与结构化 Markdown，可复制并带去生图页", async () => {
  const description = {
    model: "local-vlm", duration: 9.9, prompt: "A | woman, soft light.",
    structure: [
      { label: "构图与布局", value: "居中\n构图" },
      { label: "光线与曝光", value: "柔和侧光" },
    ],
  };
  const { page, clipboard, stored } = setup({ describeResponse: { code: 0, data: description } });
  page.setImage(png());
  await page.runDescribe();
  assert.equal(page.describing, false);
  assert.equal(page.error, "");
  assert.equal(page.description.prompt, description.prompt);
  assert.equal(page.metaLabel, "local-vlm · 耗时 9.9 秒");
  assert.equal(
    page.structureMarkdown,
    "| 维度 | 内容 |\n| --- | --- |\n| 构图与布局 | 居中 构图 |\n| 光线与曝光 | 柔和侧光 |",
  );
  await page.copy(page.structureMarkdown, "structure");
  assert.equal(clipboard[0], page.structureMarkdown);
  page.useInGenerate();
  assert.equal(stored.get("mflux.navigated"), "/");
  assert.equal(JSON.parse(stored.get("mflux.reuseGeneration")).prompt, description.prompt);
});

test("描述失败时提示错误并清空旧结果", async () => {
  const { page } = setup({ describeResponse: { code: 2306, message: "本地未找到视觉模型" } });
  page.setImage(png());
  page.description = { prompt: "旧结果", structure: [] };
  await page.runDescribe();
  assert.equal(page.description, null);
  assert.equal(page.describing, false);
  assert.match(page.error, /本地未找到视觉模型/);
});

test("更换图片会清空上一次描述结果", async () => {
  const { page } = setup({ describeResponse: { code: 0, data: { model: "vlm", duration: 1, prompt: "a", structure: [] } } });
  page.setImage(png());
  await page.runDescribe();
  assert.ok(page.description);
  page.setImage(png());
  assert.equal(page.description, null);
  assert.equal(page.copied, "");
});

test("关注点按钮支持多选，以逗号拼接并可逐个取消", async () => {
  const { page } = setup({ model: { modelId: "lmstudio-community/Qwen3-VL-8B-Instruct-MLX-4bit", cached: false } });
  await page.init();
  assert.equal(page.vlmLabel, "视觉模型未下载");
  page.applyFocus("聚焦人物");
  page.applyFocus("光线氛围");
  assert.equal(page.focus, "聚焦人物, 光线氛围");
  assert.deepEqual([...page.focusList], ["聚焦人物", "光线氛围"]);
  page.applyFocus("聚焦人物");
  assert.equal(page.focus, "光线氛围");
  // 手写关注点与预设混排时也能正确解析（兼容中文逗号）
  page.focus = "背景更亮，光线氛围";
  assert.deepEqual([...page.focusList], ["背景更亮", "光线氛围"]);
  page.applyFocus("光线氛围");
  assert.equal(page.focus, "背景更亮");
  assert.equal(page.imageSizeLabel, "");
  page.setImage(png());
  assert.match(page.imageSizeLabel, /KB$/);
});

test("未选择图片时不会发起描述请求", async () => {
  const { page } = setup();
  await page.runDescribe();
  assert.equal(page.describing, false);
  assert.equal(page.description, null);
});
