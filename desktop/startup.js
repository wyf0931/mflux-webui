import { invoke } from "@tauri-apps/api/core";

let polling = false;
async function refresh() {
  if (polling) return;
  polling = true;
  try {
    const status = await invoke("desktop_status");
    const failed = status.phase === "failed";
    document.getElementById("title").textContent = failed ? "启动未完成" : "正在启动";
    document.getElementById("message").textContent = status.message;
    document.getElementById("spinner").classList.toggle("hidden", failed);
    document.getElementById("actions").classList.toggle("hidden", !failed);
    document.getElementById("actions").classList.toggle("flex", failed);
  } catch (error) {
    document.getElementById("message").textContent = `无法读取启动状态：${error}`;
  } finally { polling = false; }
}
document.getElementById("retry").addEventListener("click", async () => {
  await invoke("desktop_retry");
  await refresh();
});
document.getElementById("logs").addEventListener("click", async () => {
  await invoke("desktop_open_logs");
});
refresh();
window.setInterval(refresh, 500);
