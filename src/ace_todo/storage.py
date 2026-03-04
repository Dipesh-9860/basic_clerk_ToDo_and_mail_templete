from pathlib import Path
import json
import sys

DATA_FILE = "todo.json"

def load_tasks(store_dir: Path) -> list[dict]:
    p = store_dir / DATA_FILE
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # fallback if file was corrupted
        backup = p.with_suffix(".corrupt.json")
        try:
            p.replace(backup)
        except Exception:
            pass
        return []

def save_tasks(store_dir: Path, tasks: list[dict]) -> None:
    p = store_dir / DATA_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")



def get_base_dir() -> Path:
    # When packaged with PyInstaller --onefile, use the EXE's folder.
    if getattr(sys, "frozen", False):           # running as a bundled exe
        return Path(sys.executable).resolve().parent
    # In dev/venv, use the project root (2 levels up from module)
    return Path(__file__).resolve().parents[2]
