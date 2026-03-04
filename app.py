from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
from pathlib import Path
from PIL import Image
import base64
import io
import requests
import os

# Import database module
from db import (
    get_settings, update_settings, get_setting,
    add_history_entry, get_all_history, delete_history, clean_history,
    get_history_by_timestamp
)

# 创建 Flask 应用
app = Flask(__name__, static_folder='static')

# 配置
IMAGES_DIR = Path(__file__).parent / "data" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# 配置静态文件路由，用于访问 data/images 中的图片
@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

# 从设置文件或环境变量加载 Ollama 地址
settings = get_settings()
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', settings.get('ollamaUrl', 'http://127.0.0.1:11434'))
if not OLLAMA_HOST.startswith('http'):
    OLLAMA_HOST = f'http://{OLLAMA_HOST}'
OLLAMA_HOST = OLLAMA_HOST.replace('0.0.0.0', '127.0.0.1')


@app.route('/')
def index():
    """主页 - 图像生成页面"""
    return render_template('index.html')


@app.route('/gallery')
def gallery():
    """画廊页面"""
    history = get_all_history()
    return render_template('gallery.html', images=history)


@app.route('/settings')
def settings():
    """设置页面"""
    return render_template('settings.html')


@app.route('/api/generate', methods=['POST'])
def generate_image():
    """API: 生成图片"""
    data = request.json
    prompt = data.get('prompt')
    model = data.get('model', 'x/flux2-klein:9b')
    width = data.get('width', 768)
    height = data.get('height', 1024)

    if not prompt:
        return jsonify({'error': '请输入 prompt'}), 400

    try:
        print(f"开始生成图片: {prompt}")
        print(f"模型: {model}, 尺寸: {width}x{height}")

        request_data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "width": width,
            "height": height,
        }

        url = f"{OLLAMA_HOST}/api/generate"
        response = requests.post(url, json=request_data, timeout=300)
        response.raise_for_status()
        response_data = response.json()

        base64_image = response_data.get("image")

        if not base64_image:
            return jsonify({'error': '生成失败：未返回图片数据'}), 500

        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{timestamp}.png"
        filepath = IMAGES_DIR / filename

        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        image.save(filepath, "PNG")

        print(f"图片已保存: {filepath}")

        total_duration = response_data.get("total_duration", 0) / 1e9

        # 保存历史记录
        history_entry = {
            "timestamp": timestamp,
            "model": model,
            "width": width,
            "height": height,
            "prompt": prompt,
            "image_path": str(filepath),
            "duration": total_duration
        }
        add_history_entry(history_entry)

        return jsonify({
            'success': True,
            'image_path': str(filepath),
            'filename': filename,
            'duration': total_duration,
            'timestamp': timestamp
        })

    except Exception as e:
        error_msg = f"生成失败：{str(e)}"
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@app.route('/api/history')
def get_history():
    """API: 获取生成历史"""
    clean_history()  # Remove entries with missing images
    return jsonify(get_all_history())


@app.route('/api/delete/<timestamp>', methods=['DELETE'])
def delete_image(timestamp):
    """API: 删除图片和历史记录"""
    try:
        entry = get_history_by_timestamp(timestamp)
        if not entry:
            return jsonify({'error': '记录不存在'}), 404

        # Delete image file
        image_path = Path(entry['image_path'])
        if image_path.exists():
            image_path.unlink()
            print(f"已删除图片: {image_path}")

        # Delete from database
        delete_history(timestamp)
        return jsonify({'success': True, 'message': '删除成功'})

    except Exception as e:
        print(f"删除失败: {e}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    """API: 获取当前设置"""
    return jsonify(get_settings())


@app.route('/api/settings', methods=['POST'])
def update_settings_api():
    """API: 更新设置"""
    try:
        data = request.json
        ollamaUrl = data.get('ollamaUrl', '').strip()

        if not ollamaUrl:
            return jsonify({'error': 'Ollama URL 不能为空'}), 400

        if not ollamaUrl.startswith('http://') and not ollamaUrl.startswith('https://'):
            ollamaUrl = f'http://{ollamaUrl}'

        settings = update_settings({'ollamaUrl': ollamaUrl})
        print(f"设置已更新: ollamaUrl = {ollamaUrl}")
        return jsonify({'success': True, 'settings': settings})

    except Exception as e:
        print(f"保存设置失败: {e}")
        return jsonify({'error': f'保存设置失败: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8090)
