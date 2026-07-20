import importlib.util
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

APP_MAIN_PATH = ROOT_DIR / "app" / "main.py"

if not APP_MAIN_PATH.exists():
    raise RuntimeError(f"Expected FastAPI module file was not bundled: {APP_MAIN_PATH}")

spec = importlib.util.spec_from_file_location("moneyplus_app_main", APP_MAIN_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load FastAPI module from: {APP_MAIN_PATH}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app
