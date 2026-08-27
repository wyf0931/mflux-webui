import Alpine from "alpinejs";

const apiClient = {
  async request(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => null);
    if (!payload || typeof payload.code !== "number") throw new Error("服务返回了无效响应");
    if (payload.code !== 0) throw new Error(payload.message || "请求失败");
    return payload.data;
  },
  get(url) { return this.request(url); },
  post(url, data) { return this.request(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }); },
  delete(url, data) { return this.request(url, { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }); },
};

const formatDuration = (value) => {
  const seconds = Math.max(0, Number(value) || 0);
  if (seconds < 60) return `${seconds.toFixed(1)}秒`;
  const minutes = Math.floor(seconds / 60); const remaining = seconds % 60;
  return minutes < 60 ? `${minutes}分${remaining.toFixed(1)}秒` : `${Math.floor(minutes / 60)}时${minutes % 60}分${remaining.toFixed(1)}秒`;
};
const formatTimestamp = (value) => value ? value.replace(/^(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2}).*$/, "$1-$2-$3 $4:$5:$6") : "—";
const formatDateTime = (value) => value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "—";

Alpine.data("theme", () => ({
  current: localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  init() { document.documentElement.dataset.theme = this.current; },
  toggle() { this.current = this.current === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = this.current; localStorage.setItem("theme", this.current); },
}));

Alpine.data("generationPage", () => ({
  models: [], result: null, error: "", submitting: false, task: null, pollTimer: null, showAdvanced: false, imageName: "选择参考图", elapsedSeconds: 0, elapsedTimer: null, reuseNotice: "",
  form: { modelId: "", prompt: "", width: 768, height: 1376, steps: 8, guidance: "", seed: "", imageStrength: 0.35 },
  preset: "portrait-9-16",
  presets: [
    { id: "square", icon: "□", ratio: "1:1", width: 1024, height: 1024 },
    { id: "landscape-4-3", icon: "▭", ratio: "4:3", width: 1184, height: 896 },
    { id: "landscape-3-2", icon: "▭", ratio: "3:2", width: 1248, height: 832 },
    { id: "landscape-16-9", icon: "▭", ratio: "16:9", width: 1376, height: 768 },
    { id: "cinema", icon: "▭", ratio: "2.35:1", width: 1568, height: 672 },
    { id: "portrait-2-3", icon: "▯", ratio: "2:3", width: 832, height: 1248 },
    { id: "portrait-9-16", icon: "▯", ratio: "9:16", width: 768, height: 1376 },
    { id: "portrait-4-5", icon: "▯", ratio: "4:5", width: 1024, height: 1280 },
    { id: "portrait-2-3-large", icon: "▯", ratio: "2:3", width: 896, height: 1344 },
  ],
  get selectedModel() { return this.models.find((model) => model.repoId === this.form.modelId); },
  get selectedPreset() { return this.presets.find((preset) => preset.id === this.preset); },
  async init() { try { this.models = (await apiClient.get("/api/models/catalog")).filter((model) => model.installed); this.form.modelId = this.models[0]?.repoId || ""; this.applyReuseParams(); } catch (error) { this.error = error.message; } },
  applyReuseParams() {
    const stored = localStorage.getItem("mflux.reuseGeneration");
    if (!stored) return;
    localStorage.removeItem("mflux.reuseGeneration");
    try {
      const params = JSON.parse(stored);
      this.form.modelId = params.modelId || this.form.modelId;
      this.form.prompt = params.prompt || "";
      this.form.width = Number(params.width) || this.form.width;
      this.form.height = Number(params.height) || this.form.height;
      this.form.steps = Number(params.steps) || this.form.steps;
      this.form.guidance = params.guidance ?? "";
      this.form.seed = params.seed ?? "";
      if (params.imageStrength !== null && params.imageStrength !== undefined) this.form.imageStrength = Number(params.imageStrength);
      this.showAdvanced = Boolean(this.form.guidance || this.form.seed || params.hasReference);
      this.syncPreset();
      if (params.hasReference) this.reuseNotice = "已恢复参数；出于浏览器安全限制，参考图文件需要重新选择。";
    } catch (_error) {
      this.reuseNotice = "历史参数读取失败，请手动填写生成参数。";
    }
  },
  applyPreset() { if (!this.selectedPreset) return; this.form.width = this.selectedPreset.width; this.form.height = this.selectedPreset.height; },
  syncPreset() { const matched = this.presets.find((preset) => preset.width === this.form.width && preset.height === this.form.height); this.preset = matched ? matched.id : "custom"; },
  chooseImage(event) { const file = event.target.files[0]; this.imageName = file ? file.name : "选择参考图"; },
  startElapsed() { this.elapsedSeconds = 0; this.elapsedTimer = window.setInterval(() => { this.elapsedSeconds += 1; }, 1000); },
  stopElapsed() { if (this.elapsedTimer) window.clearInterval(this.elapsedTimer); this.elapsedTimer = null; },
  stopPolling() { if (this.pollTimer) window.clearInterval(this.pollTimer); this.pollTimer = null; },
  elapsedLabel() { const minutes = Math.floor(this.elapsedSeconds / 60); const seconds = this.elapsedSeconds % 60; return minutes ? `${minutes}分${String(seconds).padStart(2, "0")}秒` : `${seconds}秒`; },
  etaLabel(value) { return value === null || value === undefined ? "等待中" : value <= 0 ? "即将开始" : `约 ${formatDuration(value)}`; },
  async pollTask() {
    if (!this.task?.taskId) return;
    try {
      const task = await apiClient.get(`/api/generate/tasks/${this.task.taskId}`);
      this.task = task;
      if (task.status === "succeeded") {
        this.result = { filename: task.filename, duration: task.duration, timestamp: task.timestamp };
        this.submitting = false; this.stopElapsed(); this.stopPolling();
      } else if (task.status === "failed") {
        this.error = task.error || "图片生成失败";
        this.submitting = false; this.stopElapsed(); this.stopPolling();
      }
    } catch (error) {
      this.error = error.message === "任务不存在或服务已重启" ? "服务已重启，任务未完成，请重新提交。" : error.message;
      this.submitting = false; this.stopElapsed(); this.stopPolling();
    }
  },
  async submit() {
    this.error = ""; this.result = null; this.task = null; this.stopPolling(); this.submitting = true; this.startElapsed();
    try {
      const body = new FormData(this.$refs.form);
      if (!this.$refs.image.files.length) { body.delete("image"); body.delete("imageStrength"); }
      if (!body.get("guidance")) body.delete("guidance"); if (!body.get("seed")) body.delete("seed");
      this.task = await apiClient.request("/api/generate", { method: "POST", body });
      await this.pollTask();
      if (this.submitting) this.pollTimer = window.setInterval(() => this.pollTask(), 1000);
    } catch (error) { this.error = error.message; this.submitting = false; this.stopElapsed(); }
  },
}));

Alpine.data("modelLibrary", () => ({
  catalog: [], cached: [], tasks: [], error: "", timer: null, activeSource: "huggingface", loading: true,
  get availableSources() { return [...new Set(this.catalog.map((model) => model.source))]; },
  get catalogItems() { return this.catalog.filter((model) => model.source === this.activeSource); },
  get installedItems() { return this.cached; },
  async init() { await this.load(); this.loading = false; this.timer = window.setInterval(() => this.load(), 2000); },
  async load() { try { const [catalog, cached, tasks] = await Promise.all([apiClient.get("/api/models/catalog"), apiClient.get("/api/models/cache"), apiClient.get("/api/models/downloads")]); this.catalog = catalog; this.cached = cached; this.tasks = tasks; if (!this.availableSources.includes(this.activeSource)) this.activeSource = this.availableSources[0] || "huggingface"; this.error = ""; } catch (error) { this.error = error.message; } },
  taskFor(repoId, source = "huggingface") { return this.tasks.find((task) => task.repoId === repoId && task.source === source); },
  isDownloading(repoId, source) { return ["queued", "downloading", "cancelling"].includes((this.taskFor(repoId, source) || {}).status); },
  async download(repoId, source) { try { await apiClient.post("/api/models/downloads", { repoId, source }); await this.load(); } catch (error) { this.error = error.message; } },
  async cancel(repoId, source) { try { await apiClient.delete("/api/models/downloads", { repoId, source }); await this.load(); } catch (error) { this.error = error.message; } },
  isInstalled(repoId) { return this.cached.some((model) => model.repoId === repoId); },
  formatSize(value) { return value ? `${(value / 1024 / 1024 / 1024).toFixed(1)} GB` : "大小待确认"; },
  sourceLabel(source) { return source === "modelscope" ? "ModelScope" : "Hugging Face"; },
  taskLabel(task) { return task.error || (task.currentFile ? `${task.filesDone}/${task.filesTotal} · ${task.currentFile}` : task.status); },
}));

Alpine.data("galleryPage", () => ({
  images: [], selected: "all", error: "",
  async init() { try { this.images = await apiClient.get("/api/history"); } catch (error) { this.error = error.message; } },
  get models() { return ["all", ...new Set(this.images.map((image) => image.model))]; },
  get filteredImages() { return this.selected === "all" ? this.images : this.images.filter((image) => image.model === this.selected); },
  label(model) { return model === "all" ? "全部" : model === "mflux-community/krea-2-turbo-mflux-q4" ? "Krea 2 Turbo" : model; },
  reuse(image) {
    const metadata = image.metadata || {};
    localStorage.setItem("mflux.reuseGeneration", JSON.stringify({
      modelId: image.model, prompt: image.prompt, width: image.width, height: image.height,
      steps: metadata.steps, guidance: metadata.guidance, seed: metadata.seed,
      imageStrength: metadata.imageStrength, hasReference: metadata.imageStrength !== null && metadata.imageStrength !== undefined,
    }));
    window.location.href = "/";
  },
  async remove(timestamp) { if (!confirm("确定要删除这张图片吗？此操作无法撤销。")) return; try { await apiClient.delete(`/api/history/${timestamp}`); this.images = this.images.filter((image) => image.timestamp !== timestamp); } catch (error) { this.error = error.message; } },
  async copy(prompt) { try { await navigator.clipboard.writeText(prompt); } catch (_error) { const area = document.createElement("textarea"); area.value = prompt; document.body.append(area); area.select(); document.execCommand("copy"); area.remove(); } },
  formatDuration, formatTimestamp,
}));

Alpine.data("queuePage", () => ({
  tasks: [], queueLength: 0, runningTaskId: null, error: "", timer: null,
  async init() { await this.load(); },
  destroy() { if (this.timer) window.clearInterval(this.timer); },
  async load() {
    try {
      const data = await apiClient.get("/api/generate/tasks");
      this.tasks = data.tasks; this.queueLength = data.queueLength; this.runningTaskId = data.runningTaskId; this.error = "";
      const shouldPoll = this.tasks.some((task) => ["pending", "running"].includes(task.status));
      if (shouldPoll && !this.timer) this.timer = window.setInterval(() => this.load(), 1000);
      if (!shouldPoll && this.timer) { window.clearInterval(this.timer); this.timer = null; }
    } catch (error) { this.error = error.message; }
  },
  statusLabel(status) { return ({ pending: "排队中", running: "生成中", succeeded: "已完成", failed: "失败" })[status] || status; },
  statusClass(status) { return ({ pending: "badge-warning", running: "badge-info", succeeded: "badge-success", failed: "badge-error" })[status] || "badge-ghost"; },
  etaLabel(value) { return value === null || value === undefined ? "等待中" : value <= 0 ? "即将开始" : `约 ${formatDuration(value)}`; },
  formatDateTime, formatDuration,
}));

window.apiClient = apiClient;
window.Alpine = Alpine;
Alpine.start();
