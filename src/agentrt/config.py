"""集中读取配置。所有环境变量只在这里读一次。"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent.parent

API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL: str = os.getenv("DEFAULT_MODEL", "deepseek-chat")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "traces.db"

USE_COMPRESSION = os.getenv("USE_COMPRESSION", "1") == "1"