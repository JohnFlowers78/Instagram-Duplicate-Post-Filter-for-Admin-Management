"""Fila de espera de publicacoes.

Publicacoes adicionadas a fila sao baixadas e estacionadas em DATA_DIR/waiting_queue/
ate o usuario decidir usa-las (mandar para a proxima pasta livre) ou remove-las.
A metadata fica em waiting_queue.json; as imagens em subpastas por id.
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from paths import DATA_DIR

WAITING_FILE = DATA_DIR / "waiting_queue.json"
WAITING_DIR  = DATA_DIR / "waiting_queue"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_SHORTCODE_RE = re.compile(r"/(?:p|reel|tv)/([^/?#]+)")


def shortcode_from_url(url: str) -> str:
    m = _SHORTCODE_RE.search(url or "")
    return m.group(1) if m else ""


def load_queue() -> list:
    if WAITING_FILE.exists():
        try:
            return json.loads(WAITING_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_queue(entries: list) -> None:
    WAITING_FILE.parent.mkdir(parents=True, exist_ok=True)
    WAITING_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_to_queue(url: str, media_paths: list, ig_meta: dict = None) -> dict:
    """Copia as imagens baixadas para a area da fila e registra o item.

    As imagens sao renomeadas 1, 2, 3... preservando a ordem original, para que
    organizer.save_media_to_slot consiga reaproveita-las diretamente depois.
    """
    WAITING_DIR.mkdir(parents=True, exist_ok=True)
    entry_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    item_dir = WAITING_DIR / entry_id
    item_dir.mkdir(parents=True, exist_ok=True)

    thumb = ""
    n = 0
    for idx, src in enumerate(media_paths, start=1):
        src = Path(src)
        if not src.exists():
            continue
        ext = src.suffix or ".jpg"
        dest = item_dir / f"{idx}{ext}"
        dest.write_bytes(src.read_bytes())
        if n == 0:
            thumb = str(dest)
        n += 1

    default_meta = {"views": "N/D", "likes": "N/D", "comments": "N/D", "post_date": "N/D"}
    entry = {
        "id": entry_id,
        "url": url,
        "shortcode": shortcode_from_url(url),
        "queue_datetime": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "thumbnail": thumb,
        "meta": {**default_meta, **(ig_meta or {})},
        "n_images": n,
    }
    entries = load_queue()
    entries.insert(0, entry)
    save_queue(entries)
    return entry


def entry_images(entry: dict) -> list:
    """Retorna as imagens '1.jpg', '2.png'... do item, em ordem numerica."""
    item_dir = WAITING_DIR / entry.get("id", "")
    if not item_dir.is_dir():
        return []
    imgs = [
        f for f in item_dir.iterdir()
        if f.is_file() and f.stem.isdigit() and f.suffix.lower() in IMG_EXTS
    ]
    imgs.sort(key=lambda f: int(f.stem))
    return imgs


def remove_from_queue(entry_id: str) -> None:
    """Remove o item da fila e apaga as imagens estacionadas (libera espaco)."""
    entries = load_queue()
    save_queue([e for e in entries if e.get("id") != entry_id])
    item_dir = WAITING_DIR / entry_id
    if item_dir.is_dir():
        shutil.rmtree(item_dir, ignore_errors=True)
