#!/usr/bin/env python3
"""从 data/images 目录重建 history.json"""

import json
from pathlib import Path
from datetime import datetime

IMAGES_DIR = Path(__file__).parent / "data" / "images"
HISTORY_FILE = Path(__file__).parent / "data" / "history.json"

def rebuild_history():
    """扫描图片文件并重建历史记录"""

    # 获取所有 PNG 文件
    image_files = sorted(IMAGES_DIR.glob("*.png"), reverse=True)

    if not image_files:
        print("❌ 没有找到图片文件")
        return

    print(f"📸 找到 {len(image_files)} 张图片")

    # 从文件名解析时间戳
    history = []
    for img_path in image_files:
        filename = img_path.stem  # 去掉 .png 后缀

        # 尝试解析时间戳格式: 2026-02-14-00-22-17
        try:
            timestamp = filename
            # 可以添加更多解析逻辑，从文件名或其他来源获取信息
            history_entry = {
                "timestamp": timestamp,
                "model": "x/flux2-klein:9b",  # 默认模型
                "width": 768,  # 默认尺寸
                "height": 1024,
                "prompt": "历史图片（提示词未保存）",  # 默认提示词
                "image_path": str(img_path),
                "duration": 0.0,  # 未知耗时
            }
            history.append(history_entry)
            print(f"✅ 添加: {filename}")
        except Exception as e:
            print(f"⚠️  跳过: {filename} - {e}")

    # 保存到 history.json
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已重建 {len(history)} 条历史记录")
    print(f"📄 保存到: {HISTORY_FILE}")

if __name__ == "__main__":
    rebuild_history()
