# 🎨 Ollama 图片生成 UI

基于 Flask + Ollama 的本地 AI 图片生成工具，支持响应式设计（PC + 移动端）。

## ✨ 特性

- 🚀 **本地运行**: 使用 Ollama 本地模型，无需 API 密钥
- 🎨 **响应式设计**: 完美支持 PC 端和移动端
- 🖼️ **图像画廊**: 响应式网格布局，展示所有生成的图片
- 📊 **生成统计**: 显示耗时、尺寸、模型等信息
- 💾 **自动保存**: 生成的图片自动保存到 `data/images/` 目录
- 🌐 **双页面设计**: 图像生成页面 + 画廊页面
- 📱 **移动端友好**: 汉堡菜单 + 堆叠表单布局

## 📋 前置要求

1. **Python 3.11+**
2. **Ollama 已安装并运行**
   ```bash
   # 安装 Ollama (如果未安装)
   curl -fsSL https://ollama.com/install.sh | sh

   # 启动 Ollama 服务
   ollama serve
   ```

3. **安装图片生成模型**
   ```bash
   # 示例：安装 Flux 模型
   ollama pull x/flux2-klein:9b

   # 或安装其他模型
   ollama pull x/z-image-turbo:fp8
   ```

## 🚀 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 启动应用

```bash
uv run python app.py
```

### 3. 访问应用

打开浏览器访问：**http://127.0.0.1:5000**

## 📚 使用方法

### 图像生成页面

1. **选择模型**: 在下拉菜单中选择图片生成模型
   - `x/flux2-klein:9b` (推荐)
   - `x/z-image-turbo:fp8`

2. **输入 Prompt**: 在文本框中输入图片描述

3. **调整尺寸**: 设置图片宽度和高度（256-2048，必须是 64 的倍数）

4. **生成图片**: 点击"生成图像"按钮

5. **查看结果**: 等待生成完成，查看生成的图片和统计信息

### 画廊页面

1. 点击顶部导航栏的"画廊"链接
2. 查看所有历史生成的图片
3. 点击图片可在新标签页查看大图
4. 每张图片显示：
   - 提示词（截取前 100 字符）
   - 图片尺寸（📐）
   - 使用的模型（🤖）
   - 生成耗时（⏱️）
   - 时间戳

## 💡 Prompt 示例

```
一颗苹果，挂在苹果树上，近景，聚集，插画风格
一片火龙果田地，镜头下的火龙果树挂了几颗火龙果，插画风格，近景
一串葡萄，插画风格，田园，近景
一串草莓，插图风格，田园风景，近景
一颗大西瓜，插画风格，背景在西瓜地，近景
枇杷，绿叶，黄色枇杷，古代传统庭院，近景
```

## 📁 项目结构

```
ollama-image-generate-ui/
├── app.py                    # Flask 主应用
├── templates/
│   ├── base.html            # 基础模板（导航栏）
│   ├── index.html           # 图像生成页面
│   └── gallery.html         # 画廊页面
├── static/
│   └── css/
│       └── style.css        # 全局样式
├── data/
│   ├── images/              # 生成的图片保存目录
│   └── history.json         # 历史记录
├── .planning/               # 项目规划文件
├── pyproject.toml           # 项目配置
└── README.md               # 项目说明
```

## 🔧 配置选项

### Ollama API 地址

默认使用 `http://127.0.0.1:11434`，可通过环境变量修改：

```bash
export OLLAMA_HOST=http://192.168.1.100:11434
uv run python app.py
```

### 图片尺寸限制

- **最小**: 256 × 256
- **最大**: 2048 × 2048
- **步长**: 64

### 历史记录

- 自动保存最近 100 条生成记录
- 历史记录保存在 `data/history.json`
- 图片保存在 `data/images/` 目录

## 🎯 API 端点

### POST /api/generate

生成新图片

**请求体**:
```json
{
  "prompt": "一颗苹果",
  "model": "x/flux2-klein:9b",
  "width": 768,
  "height": 1024
}
```

**响应**:
```json
{
  "success": true,
  "image_path": "/path/to/image.png",
  "filename": "2026-02-14-00-22-17.png",
  "duration": 53.2,
  "timestamp": "2026-02-14-00-22-17"
}
```

### GET /api/history

获取生成历史

**响应**:
```json
[
  {
    "timestamp": "2026-02-14-00-22-17",
    "model": "x/flux2-klein:9b",
    "width": 768,
    "height": 1024,
    "prompt": "一片火龙果田地...",
    "image_path": "/path/to/image.png",
    "duration": 53.2
  }
]
```

### GET /static/images/<filename>

获取生成的图片

## 🐛 故障排除

### 找不到图片生成模型

确保：
1. Ollama 服务正在运行 (`ollama serve`)
2. 已安装 `x/` 开头的模型 (`ollama pull x/flux2-klein:9b`)
3. 模型名称正确（区分大小写）

### 无法连接到 Ollama API

检查：
1. Ollama 服务是否运行: `ps aux | grep ollama`
2. API 地址是否正确: `curl http://127.0.0.1:11434/api/tags`
3. 防火墙设置

### 画廊图片无法显示

检查：
1. `data/images/` 目录是否存在且有图片文件
2. Flask 应用是否有权限读取该目录
3. 浏览器控制台是否有错误信息

## 📚 技术栈

- **Flask**: Python Web 框架
- **Jinja2**: 模板引擎
- **Ollama**: 本地 LLM 推理和图片生成
- **Pillow**: 图片处理
- **Requests**: HTTP 请求
- **HTML5/CSS3**: 响应式设计
- **JavaScript**: 前端交互

## 🚀 部署建议

### 生产环境部署

1. **使用生产级 WSGI 服务器**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **配置反向代理**（Nginx）
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:5000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

3. **设置环境变量**
   ```bash
   export FLASK_ENV=production
   export OLLAMA_HOST=http://127.0.0.1:11434
   ```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
