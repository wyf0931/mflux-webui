from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename

from db import (
    add_history_entry, get_all_history, delete_history, clean_history,
    get_history_by_timestamp
)
from mflux_service import MfluxService
from model_cache import get_cached_models

# 创建 Flask 应用
app = Flask(__name__, static_folder='static')

# 配置
IMAGES_DIR = Path(__file__).parent / "data" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _mflux_service():
    return MfluxService(IMAGES_DIR)


@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route('/')
def index():
    """主页 - 图像生成页面"""
    return render_template('index.html')


@app.route('/gallery')
def gallery():
    """画廊页面"""
    history = get_all_history()
    return render_template('gallery.html', images=history)


@app.route('/models')
def models():
    """本地 Hugging Face 模型缓存页面。"""
    return render_template('models.html')


@app.route('/api/models/cache')
def get_model_cache_api():
    """API：只读获取本机 Hugging Face 模型缓存。"""
    return jsonify(get_cached_models())


@app.route('/api/generate', methods=['POST'])
def generate_image():
    """API: 生成图片"""
    data = (request.get_json(silent=True) or {}) if request.is_json else request.form
    prompt = data.get('prompt')
    width = data.get('width', 768)
    height = data.get('height', 1024)

    if not prompt:
        return jsonify({'error': '请输入 prompt'}), 400

    input_path = None
    try:
        input_image = request.files.get('image')
        if input_image and input_image.filename:
            suffix = Path(secure_filename(input_image.filename)).suffix.lower()
            if suffix not in {'.png', '.jpg', '.jpeg', '.webp'}:
                return jsonify({'error': '参考图仅支持 PNG、JPG、JPEG 或 WebP'}), 400
            uploads_dir = IMAGES_DIR.parent / 'uploads'
            uploads_dir.mkdir(parents=True, exist_ok=True)
            input_path = uploads_dir / f'{uuid4().hex}{suffix}'
            input_image.save(input_path)
        result = _mflux_service().generate(
            prompt=prompt,
            width=width,
            height=height,
            seed=data.get('seed'),
            steps=data.get('steps'),
            guidance=data.get('guidance'),
            input_image=input_path,
            image_strength=data.get('imageStrength'),
        )

        print(f"图片已保存: {result.image_path} ({result.duration:.1f}s)")

        # 保存历史记录
        timestamp = result.filename.replace('.png', '')
        history_entry = {
            "timestamp": timestamp,
            "model": result.model,
            "width": result.width,
            "height": result.height,
            "prompt": result.prompt,
            "image_path": result.image_path,
            "duration": result.duration,
            "metadata": result.metadata,
        }
        add_history_entry(history_entry)

        return jsonify({
            'success': True,
            'image_path': result.image_path,
            'filename': result.filename,
            'duration': result.duration,
            'timestamp': timestamp,
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'生成失败：{str(e)}'}), 500
    finally:
        if input_path and input_path.exists():
            input_path.unlink()


@app.route('/api/history')
def get_history():
    """API: 获取生成历史"""
    clean_history()
    return jsonify(get_all_history())


@app.route('/api/delete/<timestamp>', methods=['DELETE'])
def delete_image(timestamp):
    """API: 删除图片和历史记录"""
    try:
        entry = get_history_by_timestamp(timestamp)
        if not entry:
            return jsonify({'error': '记录不存在'}), 404

        image_path = Path(entry['image_path'])
        if image_path.exists():
            image_path.unlink()
            print(f"已删除图片: {image_path}")

        delete_history(timestamp)
        return jsonify({'success': True, 'message': '删除成功'})

    except Exception as e:
        print(f"删除失败: {e}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8090)
