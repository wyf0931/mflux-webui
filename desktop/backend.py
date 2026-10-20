"""桌面后端入口：启动配置通过 stdin 传入，不依赖用户的 Python 环境。"""

import argparse
import json
import logging
import multiprocessing
import os
import secrets
import sys
import threading
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def protect_desktop_app(app, token, port, data_dir=None):
    """仅允许经过启动握手的本机会话访问桌面服务。"""
    from flask import abort, request

    origin = f"http://127.0.0.1:{port}"
    cookie_name = f"mflux_desktop_{port}"
    bootstrap_used = False
    preferences_file = Path(data_dir) / "preferences.json" if data_dir else None
    theme = "rausch"
    if preferences_file and preferences_file.is_file():
        try:
            theme = json.loads(preferences_file.read_text(encoding="utf-8")).get("theme", theme)
        except (OSError, ValueError, AttributeError):
            app.logger.warning("无法读取桌面主题设置，使用默认主题")
    app.config["DESKTOP_THEME"] = theme if theme in ("rausch", "rausch-dark") else "rausch"
    preferences_lock = threading.Lock()

    @app.context_processor
    def desktop_context():
        return {"desktop_theme": app.config["DESKTOP_THEME"]}

    @app.post("/desktop/theme")
    def save_theme():
        data = request.get_json(silent=True)
        theme = data.get("theme") if isinstance(data, dict) else None
        if theme not in ("rausch", "rausch-dark"):
            abort(400)
        with preferences_lock:
            if preferences_file:
                temporary = preferences_file.with_suffix(".tmp")
                temporary.write_text(json.dumps({"theme": theme}), encoding="utf-8")
                temporary.replace(preferences_file)
            app.config["DESKTOP_THEME"] = theme
        return {"code": 0, "data": None, "message": "ok"}

    @app.before_request
    def authenticate():
        if request.host != f"127.0.0.1:{port}":
            abort(403)
        if request.path == "/desktop/bootstrap":
            return
        if not secrets.compare_digest(request.cookies.get(cookie_name, ""), token):
            abort(403)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.headers.get("Origin", origin) != origin:
            abort(403)

    @app.get("/desktop/bootstrap")
    def bootstrap():
        nonlocal bootstrap_used
        if bootstrap_used or not secrets.compare_digest(request.args.get("token", ""), token):
            abort(403)
        bootstrap_used = True
        # 首次导航来自 tauri://，WKWebView 在同一跨站重定向链中不会发送 Strict Cookie。
        # 先完成本机文档加载，再由同源文档进入首页，避免降低会话 Cookie 的保护。
        response = app.response_class(
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<title>mflux WebUI</title><script>location.replace("/")</script>'
            '<a href="/">打开 mflux WebUI</a></html>', mimetype="text/html",
        )
        response.set_cookie(cookie_name, token, httponly=True, samesite="Strict")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.after_request
    def desktop_headers(response):
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response


def self_test():
    """在冻结环境实际导入全部模型，并执行一次 Metal 运算（不下载权重）。"""
    import mlx.core as mx
    from mflux.models.common.config import ModelConfig
    from mflux.models.flux2 import Flux2Klein
    from mflux.models.krea2 import Krea2
    from mflux.models.qwen21.variants.edit.qwen_image_21_edit import QwenImage21Edit
    from mflux.models.qwen21.variants.txt2img.qwen_image_21 import QwenImage21
    from mflux.models.z_image import ZImageTurbo
    from modelscope.hub.snapshot_download import snapshot_download
    from transformers import AutoTokenizer, Qwen2TokenizerFast

    mx.set_default_device(mx.gpu)
    result = mx.sum(mx.array([1.0, 2.0, 3.0])).item()
    if result != 6.0:
        raise RuntimeError("Metal 运算自检失败")
    print(json.dumps({"metal": True, "tokenizers": [AutoTokenizer.__name__, Qwen2TokenizerFast.__name__],
                      "modelscope": callable(snapshot_download), "models": [
        ModelConfig.__name__, Flux2Klein.__name__, Krea2.__name__,
        QwenImage21.__name__, QwenImage21Edit.__name__, ZImageTurbo.__name__,
    ]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return

    config = json.loads(sys.stdin.readline())
    token = config["token"]
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("桌面会话令牌无效")
    data_dir = Path(config["dataDir"]).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MFLUX_DATA_DIR"] = str(data_dir)

    # Rust 保持 stdin 管道打开；即使桌面外壳异常退出，也不会残留后端。
    def watch_parent():
        sys.stdin.read()
        os._exit(0)

    threading.Thread(target=watch_parent, daemon=True, name="desktop-parent").start()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    # 避免把启动 URL 中的会话令牌写入访问日志。
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    from werkzeug.serving import make_server

    from mflux_webui import app

    server = make_server("127.0.0.1", 0, app, threaded=True)
    protect_desktop_app(app, token, server.server_port, data_dir)
    print(json.dumps({"event": "ready", "port": server.server_port}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
