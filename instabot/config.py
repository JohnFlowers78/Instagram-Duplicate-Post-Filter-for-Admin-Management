import json
from pathlib import Path

from paths import DATA_DIR

CONFIG_PATH = DATA_DIR / "config.json"

DEFAULTS = {
    "db_folder": "",
    "person_initial": "V",
    "slots_per_day": 6,
    "hash_threshold": 5,
    "include_day_counter": True,
    "include_person_initial": True,
    "theme": "light",
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
