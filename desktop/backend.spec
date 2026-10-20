# PyInstaller 目录式后端；仅收集运行资源，不把权重、用户配置和历史打入安装包。
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata, get_package_paths

root = Path(SPECPATH).parent
datas = [
    (str(root / "mflux_webui/templates"), "mflux_webui/templates"),
    (str(root / "mflux_webui/static"), "mflux_webui/static"),
    (str(root / "config/models.json"), "config"),
    (str(root / "LICENSE"), "licenses/mflux-webui"),
]
for package in ("mflux", "mlx", "transformers", "modelscope"):
    datas += collect_data_files(package)
for distribution in ("mflux", "mlx", "mlx-metal", "modelscope"):
    datas += copy_metadata(distribution)

# TokenizerLoader 通过字符串查找这些类，静态分析无法发现。
hiddenimports = [
    "transformers.models.auto.tokenization_auto",
    "transformers.models.clip.tokenization_clip",
    "transformers.models.t5.tokenization_t5",
    "transformers.models.qwen2.tokenization_qwen2",
    "transformers.models.qwen2_vl.image_processing_pil_qwen2_vl",
    "sentencepiece",
    "socksio",
]
# MLX 的 C++ 扩展会动态导入 Python 辅助模块，无法仅靠 Python import 图收集。
mlx_path = Path(get_package_paths("mlx")[1])
for source in mlx_path.rglob("*.py"):
    parts = list(source.relative_to(mlx_path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    hiddenimports.append(".".join(["mlx", *parts]))
a = Analysis(
    [str(root / "desktop/backend.py")],
    pathex=[str(root)],
    binaries=collect_dynamic_libs("mlx"),
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "IPython", "pytest", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="mflux-backend", console=True, strip=False, upx=False,
    target_arch="arm64",
    codesign_identity=os.environ.get("APPLE_SIGNING_IDENTITY") or None,
    entitlements_file=str(root / "src-tauri/Entitlements.plist"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="backend")
