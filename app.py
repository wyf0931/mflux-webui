"""mflux WebUI 应用入口：仅负责页面壳、静态文件与 API 装配。"""

from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory

from api import api, failure


def create_app():
    app = Flask(__name__, static_folder="static")
    images_dir = Path(__file__).parent / "data" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.config["IMAGES_DIR"] = str(images_dir)
    app.register_blueprint(api)

    @app.template_filter("timestamp")
    def format_timestamp(value):
        for pattern in ("%Y-%m-%d-%H-%M-%S-%f", "%Y-%m-%d-%H-%M-%S"):
            try:
                return datetime.strptime(value, pattern).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                continue
        return value

    @app.template_filter("duration")
    def format_duration(value):
        try:
            seconds = max(0, float(value))
        except (TypeError, ValueError):
            return "—"
        if seconds < 60:
            return f"{seconds:.1f}秒"
        minutes, remaining = divmod(seconds, 60)
        if minutes < 60:
            return f"{int(minutes)}分{remaining:.1f}秒"
        hours, minutes = divmod(int(minutes), 60)
        return f"{hours}时{minutes}分{remaining:.1f}秒"

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/gallery")
    def gallery():
        return render_template("gallery.html")

    @app.get("/models")
    def models():
        return render_template("models.html")

    @app.get("/static/images/<filename>")
    def serve_image(filename):
        return send_from_directory(app.config["IMAGES_DIR"], filename)

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return failure("接口不存在", code=2404, status=404)
        return _error

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8090)
