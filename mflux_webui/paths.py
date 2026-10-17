"""统一只读资源与可写数据路径，兼容源码和冻结的桌面运行环境。"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR = Path(os.environ.get("MFLUX_DATA_DIR", PROJECT_ROOT / "data")).expanduser().resolve()
