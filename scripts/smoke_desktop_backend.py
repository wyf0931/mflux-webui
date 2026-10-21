"""验证打包后端的页面、资源、会话及退出，无需 GPU 或模型权重。"""

import argparse
import http.cookiejar
import json
import os
import queue
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", type=Path)
    parser.add_argument("--generate-model", help="使用已有缓存验证实际生图，不下载权重")
    args = parser.parse_args()
    executable = args.backend.resolve()
    mlx_alias = executable.parent / "_internal/libmlx.dylib"
    assert mlx_alias.is_symlink(), "MLX 库链接必须保留；普通资源复制会破坏 metallib 查找并使安装包变大"
    with tempfile.TemporaryDirectory(prefix="mflux-desktop-test-") as temporary:
        token = secrets.token_hex(32)
        cache_environment = {} if args.generate_model else {
            "HF_HOME": str(Path(temporary) / "huggingface"),
            "HF_HUB_CACHE": str(Path(temporary) / "huggingface/hub"),
            "MODELSCOPE_CACHE": str(Path(temporary) / "modelscope"),
        }
        process = subprocess.Popen([str(executable)], cwd=temporary,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                   env={**os.environ, **cache_environment, "HF_HUB_OFFLINE": "1"})
        try:
            process.stdin.write(json.dumps({"token": token, "dataDir": temporary}) + "\n")
            process.stdin.flush()
            startup = queue.Queue()
            threading.Thread(target=lambda: startup.put(process.stdout.readline()), daemon=True).start()
            ready = json.loads(startup.get(timeout=90))
            assert ready["event"] == "ready", ready
            threading.Thread(target=lambda: shutil.copyfileobj(process.stdout, sys.stderr), daemon=True).start()
            origin = f"http://127.0.0.1:{ready['port']}"
            try:
                urllib.request.urlopen(origin + "/", timeout=10)
                raise AssertionError("未授权请求应被拒绝")
            except urllib.error.HTTPError as error:
                assert error.code == 403, error
            cookies = http.cookiejar.CookieJar()
            client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
            client.open(f"{origin}/desktop/bootstrap?token={token}", timeout=10).read()
            for route in ("/", "/describe", "/models", "/gallery", "/queue", "/static/css/app.css", "/static/js/app.js",
                          "/api/models/cache", "/api/models/catalog", "/api/generate/tasks", "/api/history"):
                try:
                    response = client.open(origin + route, timeout=15)
                except urllib.error.HTTPError as error:
                    raise AssertionError(f"{route} 返回 HTTP {error.code}：{error.read().decode()}") from error
                assert response.status == 200, (route, response.status)
                assert response.read(), route
            catalog = json.load(client.open(origin + "/api/models/catalog", timeout=15))["data"]
            assert catalog, "首次启动必须仍然提供模型下载目录"
            if not args.generate_model:
                assert all(not model["installed"] for model in catalog), "空缓存不能报告已安装模型"
            assert (Path(temporary) / "db.json").is_file()
            theme_request = urllib.request.Request(origin + "/desktop/theme",
                data=b'{"theme":"rausch-dark"}',
                headers={"Content-Type": "application/json", "Origin": origin})
            assert json.load(client.open(theme_request, timeout=10))["code"] == 0
            assert json.loads((Path(temporary) / "preferences.json").read_text())["theme"] == "rausch-dark"
            assert b'data-theme="rausch-dark"' in client.open(origin + "/", timeout=10).read()
            if args.generate_model:
                request = urllib.request.Request(origin + "/api/generate", data=json.dumps({
                    "modelId": args.generate_model, "prompt": "一只红色的小猫，白色背景", "width": 256,
                    "height": 256, "steps": 1, "seed": 42,
                }).encode(), headers={"Content-Type": "application/json", "Origin": origin})
                result = json.load(client.open(request, timeout=15))
                assert result["code"] == 0, result
                task_id = result["data"]["taskId"]
                deadline = time.monotonic() + 600
                while time.monotonic() < deadline:
                    task = json.load(client.open(f"{origin}/api/generate/tasks/{task_id}", timeout=15))["data"]
                    if task["status"] == "failed":
                        raise AssertionError(f"打包生图失败：{task.get('error')}\n{task.get('logs', '')}")
                    if task["status"] == "succeeded":
                        image = client.open(f"{origin}/static/images/{task['filename']}", timeout=15).read()
                        assert image.startswith(b"\x89PNG\r\n\x1a\n"), "输出必须是有效 PNG"
                        print(f"独立后端实际生图通过：{args.generate_model}，{len(image)} 字节 PNG。")
                        break
                    time.sleep(2)
                else:
                    raise TimeoutError("生图验证超过 10 分钟")
            process.stdin.close()
            assert process.wait(timeout=10) == 0, "父进程管道关闭后应正常退出"
            print("打包后端验证通过：页面、静态资源、模型目录、队列、历史、会话与退出。")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
