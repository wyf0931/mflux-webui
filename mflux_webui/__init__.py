"""mflux WebUI Flask 应用工厂与页面路由。"""

from datetime import UTC, datetime

from flask import Flask, render_template, request, send_from_directory

from .api import api as _api
from .api import failure
from .generation_tasks import GenerationTaskManager
from .paths import DATA_DIR
from .vlm_service import VlmService


def create_app():
    """创建 Flask 应用实例，便于测试、开发和部署环境复用。"""
    app = Flask(__name__)
    images_dir = DATA_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.config["IMAGES_DIR"] = str(images_dir)
    app.register_blueprint(_api)
    app.extensions["generation_task_manager"] = GenerationTaskManager(images_dir)
    app.extensions["vlm_service"] = VlmService()

    @app.template_filter("timestamp")
    def format_timestamp(value):
        for pattern in ("%Y-%m-%d-%H-%M-%S-%f", "%Y-%m-%d-%H-%M-%S"):
            try:
                return datetime.strptime(value, pattern).replace(tzinfo=UTC).strftime("%Y-%m-%d %H:%M:%S")
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

    @app.get("/describe")
    def describe():
        return render_template("describe.html")

    @app.get("/models")
    def models():
        return render_template("models.html")

    @app.get("/queue")
    def generation_queue():
        return render_template("queue.html")

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
