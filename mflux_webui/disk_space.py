"""磁盘空间预检。

生成、下载和桌面后端启动都会写入数据目录或缓存目录。磁盘耗尽时，冻结的桌面
后端会在 PyInstaller 运行钩子里直接失败（`No usable temporary directory`），
整个应用随之退出。因此在开始工作前先检查剩余空间，并给出可操作的提示。
"""

from __future__ import annotations

import shutil
from pathlib import Path

GIB = 1024**3

# 生成一张图片本身只有几 MB，但 macOS 在内存压力下会用磁盘换页，
# 留出 2 GB 余量可以覆盖换页与历史写入，避免生成中途磁盘写满。
GENERATION_MIN_FREE_BYTES = 2 * GIB

# 下载使用 SDK 的临时文件与分片，权重之外额外留 2 GB。
DOWNLOAD_EXTRA_FREE_BYTES = 2 * GIB


class InsufficientSpaceError(RuntimeError):
    """剩余磁盘空间不足，继续执行会写满磁盘。"""

    def __init__(self, required_bytes, available_bytes, location, action):
        self.required_bytes = int(required_bytes)
        self.available_bytes = int(available_bytes)
        self.location = str(location)
        self.action = action
        super().__init__(
            f"磁盘空间不足：{action}至少需要 {format_size(self.required_bytes)}，"
            f"当前剩余 {format_size(self.available_bytes)}。"
            "请清理磁盘后重试。"
        )


def format_size(value):
    """按 GB / MB 输出便于阅读的容量。"""
    value = max(0, int(value))
    if value >= GIB:
        return f"{value / GIB:.1f} GB"
    return f"{value / 1024**2:.0f} MB"


def free_bytes(path):
    """返回路径所在卷的剩余空间；路径不存在时向上查找最近的已存在目录。"""
    target = Path(path)
    for candidate in [target, *target.parents]:
        if candidate.exists():
            try:
                return int(shutil.disk_usage(candidate).free)
            except OSError:
                return 0
    return 0


def check_generation_space(path, required_bytes=GENERATION_MIN_FREE_BYTES):
    """生成前检查数据目录所在卷的空间。"""
    available = free_bytes(path)
    if available < required_bytes:
        raise InsufficientSpaceError(required_bytes, available, path, "生成图片")
    return available


def check_download_space(path, model_bytes=0, extra_bytes=DOWNLOAD_EXTRA_FREE_BYTES):
    """下载前检查缓存目录所在卷的空间，模型体积之外再留出余量。"""
    required = max(0, int(model_bytes)) + extra_bytes
    available = free_bytes(path)
    if available < required:
        raise InsufficientSpaceError(required, available, path, "下载模型")
    return available
