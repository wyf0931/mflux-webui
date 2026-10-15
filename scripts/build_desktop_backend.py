"""构建可独立运行的 Apple Silicon 后端，并准备 Tauri 的启动页资源。"""

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def verify_macos_version(directory):
    """核对原生库的真实最低版本，避免 wheel 标签与 Mach-O 声明不一致。"""
    magic_values = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
    for path in directory.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as binary:
            if binary.read(4) not in magic_values:
                continue
        metadata = subprocess.run(["otool", "-l", str(path)], check=True, capture_output=True, text=True).stdout
        for version in re.findall(r"\bminos\s+([\d.]+)", metadata):
            if tuple(int(part) for part in version.split(".")) > (14, 0):
                raise RuntimeError(f"{path.name} 要求 macOS {version}，超过桌面版声明的 macOS 14.0")


def main():
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("桌面安装包只能在 Apple Silicon Mac 上构建。")
    frontend = ROOT / "build/desktop/frontend"
    frontend.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "desktop/index.html", frontend / "index.html")
    shutil.copy2(ROOT / "mflux_webui/static/css/app.css", frontend / "app.css")
    subprocess.run([
        str(ROOT / "node_modules/.bin/esbuild"),
        str(ROOT / "desktop/startup.js"), "--bundle", "--minify",
        f"--outfile={frontend / 'startup.js'}",
    ], check=True, cwd=ROOT)
    # 明确选择 macOS 14 的 wheel，避免在新系统上构建时自动带入更高最低版本的 MLX。
    build_environment = ROOT / "build/desktop-env"
    build_env = {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(build_environment),
        "MACOSX_DEPLOYMENT_TARGET": "14.0",
        "PYINSTALLER_CONFIG_DIR": str(ROOT / "build/pyinstaller-cache"),
        "MPLCONFIGDIR": str(ROOT / "build/matplotlib-cache"),
    }
    subprocess.run([
        "uv", "sync", "--locked", "--group", "desktop", "--python", "3.11",
        "--python-platform", "aarch64-apple-darwin",
    ], check=True, cwd=ROOT, env=build_env)
    subprocess.run([
        str(build_environment / "bin/python"), "-m", "PyInstaller", "--noconfirm",
        "--distpath", str(ROOT / "build/desktop"),
        "--workpath", str(ROOT / "build/pyinstaller"),
        str(ROOT / "desktop/backend.spec"),
    ], check=True, cwd=ROOT, env=build_env)
    verify_macos_version(ROOT / "build/desktop/backend")
    print(f"桌面后端已生成：{ROOT / 'build/desktop/backend/mflux-backend'}")


if __name__ == "__main__":
    main()
