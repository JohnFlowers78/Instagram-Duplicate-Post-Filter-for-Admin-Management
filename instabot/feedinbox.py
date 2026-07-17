"""Inbox do Feed Especial ("Instagram Saudavel").

Este arquivo e o CONTRATO entre o coletor (feedbot) e o app: o coletor so
ESCREVE itens aqui; o app so LE e muda status. Quando o coletor for para uma
VM/cloud (Fase 3), basta sincronizar este arquivo — nada mais muda.

Estrutura (DATA_DIR/feed_inbox.json):
  {"feeds": [{id, name, created, last_collect, config{...}, items[...]}]}

Item: {id, shortcode, url, likes, comments, likes_n, comments_n, caption,
       thumb, carousel, found_at, status}
  status: "new" (aparece no feed) | "saved" (virou Salvos) | "discarded"
  (descartada — vira exemplo NEGATIVO do filtro de gosto na Fase 2).

Thumbnails ficam em DATA_DIR/feed_media/<feed_id>/<item_id>.jpg.
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from paths import DATA_DIR

INBOX_FILE = DATA_DIR / "feed_inbox.json"
MEDIA_DIR = DATA_DIR / "feed_media"

MAX_ITEMS_PER_FEED = 1000   # margem definida no design (500-1000)

DEFAULT_CONFIG = {
    "likes_min": 20000,      # faixa de likes (20k a 1M por padrao)
    "likes_max": 1000000,
    "comments_min": 200,     # limiar SEPARADO p/ comentarios (20k seria rarissimo)
    "only_carousels": True,
    "scroll_minutes": 10,    # duracao de cada coleta
}


def load() -> dict:
    if INBOX_FILE.exists():
        try:
            data = json.loads(INBOX_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "feeds" in data:
                return data
        except Exception:
            pass
    return {"feeds": []}


def save(data: dict) -> None:
    INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INBOX_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_or_create_default_feed() -> dict:
    """MVP: um unico feed. (O formato ja suporta varios — Fase 2+.)"""
    data = load()
    if data["feeds"]:
        feed = data["feeds"][0]
        # garante chaves novas de config em inboxes antigos
        cfg = {**DEFAULT_CONFIG, **(feed.get("config") or {})}
        if cfg != feed.get("config"):
            feed["config"] = cfg
            save(data)
        return feed
    feed = {
        "id": uuid.uuid4().hex,
        "name": "Feed 1",
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "last_collect": "",
        "config": dict(DEFAULT_CONFIG),
        "items": [],
    }
    data["feeds"].append(feed)
    save(data)
    return feed


def get_feed(feed_id: str, data=None):
    data = data if data is not None else load()
    for f in data.get("feeds", []):
        if f.get("id") == feed_id:
            return f
    return None


def update_config(feed_id: str, cfg: dict) -> None:
    data = load()
    f = get_feed(feed_id, data)
    if f is not None:
        f["config"] = {**DEFAULT_CONFIG, **(f.get("config") or {}), **cfg}
        save(data)


def set_last_collect(feed_id: str, stamp: str) -> None:
    data = load()
    f = get_feed(feed_id, data)
    if f is not None:
        f["last_collect"] = stamp
        save(data)


def known_shortcodes(feed_id: str, data=None) -> set:
    f = get_feed(feed_id, data)
    if not f:
        return set()
    return {it.get("shortcode", "") for it in f.get("items", [])}


def feed_thumb_dir(feed_id: str) -> Path:
    d = MEDIA_DIR / feed_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def add_item(feed_id: str, shortcode: str, likes_disp: str, comments_disp: str,
             likes_n, comments_n, caption: str, thumb_path: str,
             carousel: bool) -> dict:
    """Acrescenta um item coletado (status 'new') e aplica o teto do buffer."""
    data = load()
    f = get_feed(feed_id, data)
    if f is None:
        return {}
    item = {
        "id": uuid.uuid4().hex,
        "shortcode": shortcode,
        "url": f"https://www.instagram.com/p/{shortcode}/",
        "likes": likes_disp or "N/D",
        "comments": comments_disp or "N/D",
        "likes_n": likes_n,
        "comments_n": comments_n,
        "caption": (caption or "")[:400],
        "thumb": thumb_path or "",
        "carousel": bool(carousel),
        "found_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "new",
    }
    f.setdefault("items", []).append(item)
    _trim(f)
    save(data)
    return item


def _trim(feed: dict) -> None:
    """Teto do buffer: descarta primeiro as mais antigas ja resolvidas
    (saved/discarded); so entao as 'new' mais antigas."""
    items = feed.get("items", [])
    excess = len(items) - MAX_ITEMS_PER_FEED
    if excess <= 0:
        return
    keep = []
    resolved_old = [it for it in items if it.get("status") != "new"]
    to_drop = set()
    for it in resolved_old[:excess]:
        to_drop.add(it.get("id"))
    excess -= len(to_drop)
    if excess > 0:
        for it in items:
            if it.get("status") == "new" and excess > 0 and it.get("id") not in to_drop:
                to_drop.add(it.get("id"))
                excess -= 1
    for it in items:
        if it.get("id") in to_drop:
            _delete_thumb(it)
        else:
            keep.append(it)
    feed["items"] = keep


def _delete_thumb(item: dict) -> None:
    tp = item.get("thumb", "")
    if tp:
        try:
            Path(tp).unlink(missing_ok=True)
        except OSError:
            pass


def set_item_status(feed_id: str, item_id: str, status: str) -> None:
    data = load()
    f = get_feed(feed_id, data)
    if f is None:
        return
    for it in f.get("items", []):
        if it.get("id") == item_id:
            it["status"] = status
            save(data)
            return


def items_by_status(feed_id: str, status: str = "new", data=None) -> list:
    f = get_feed(feed_id, data)
    if not f:
        return []
    return [it for it in f.get("items", []) if it.get("status") == status]


def counts(feed_id: str, data=None) -> dict:
    f = get_feed(feed_id, data)
    out = {"new": 0, "saved": 0, "discarded": 0}
    for it in (f.get("items", []) if f else []):
        s = it.get("status", "new")
        out[s] = out.get(s, 0) + 1
    return out


def clear_feed(feed_id: str) -> None:
    """Esvazia o feed (itens + thumbnails). As publicacoes salvas ja estao nos
    Salvos do app — aqui so limpa o buffer de descobertas."""
    data = load()
    f = get_feed(feed_id, data)
    if f is None:
        return
    for it in f.get("items", []):
        _delete_thumb(it)
    f["items"] = []
    save(data)
    try:
        shutil.rmtree(MEDIA_DIR / feed_id, ignore_errors=True)
    except Exception:
        pass
