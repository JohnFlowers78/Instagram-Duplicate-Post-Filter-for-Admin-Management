import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "data" / "config.json"

DEFAULTS = {
    "db_folder": "",
    "person_initial": "V",
    "slots_per_day": 6,
    "hash_threshold": 5,
}


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = DEFAULTS.copy()
        merged.update(data)
        return merged
    return DEFAULTS.copy()


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
