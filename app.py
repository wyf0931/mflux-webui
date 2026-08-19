"""兼容旧启动命令的入口；实际 Flask 应用位于 mflux_webui 包内。"""

from mflux_webui import app, create_app

__all__ = ["app", "create_app"]

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8090)
