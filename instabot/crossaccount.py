"""Listas nomeadas do 'Filtro Entre Contas'.

Cada lista corresponde a uma conta/cliente de origem. Ao analisar uma pasta de
origem inteira, cada publicacao (subpasta com imagens) vira um item da lista.

Os itens REFERENCIAM as imagens diretamente na pasta de origem (nao copiam —
uma conta pode ter centenas de publicacoes). Os hashes ja calculados ficam
guardados no item para comparacoes rapidas (ex.: no Recarregar).

Flags de estado por item:
  - duplicate: ja existe na Pasta de Destino (base de comparacao)
  - used: ja foi enviada para uma pasta do dia (esta no Historico)
Qualquer um dos dois deixa o item "cinza" (indisponivel) na UI.

Persistido em cross_lists.json (dentro de DATA_DIR).
"""

import json
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from paths import DATA_DIR

CROSS_FILE = DATA_DIR / "cross_lists.json"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def load() -> dict:
    if CROSS_FILE.exists():
        try:
            data = json.loads(CROSS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "lists" in data:
                return data
        except Exception:
            pass
    return {"active": "", "lists": []}


def save(data: dict) -> None:
    CROSS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CROSS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _sorted_images(folder: Path) -> list:
    if not folder.is_dir():
        return []
    imgs = [
        f for f in folder.iterdir()
        if f.is_file() and f.stem.isdigit() and f.suffix.lower() in IMG_EXTS
    ]
    imgs.sort(key=lambda f: int(f.stem))
    return imgs


def find_publication_folders(root) -> list:
    """Enumera as pastas de publicacao (carrosseis) dentro da pasta de origem.

    Aceita tanto o padrao Dia_X/pasta_N (2 niveis) quanto publicacoes em
    subpastas diretas. Retorna as pastas que contem imagens numeradas.
    """
    root = Path(root)
    found = []
    if not root.is_dir():
        return found
    for sub in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not sub.is_dir():
            continue
        if _sorted_images(sub):          # publicacao direta (nivel 1)
            found.append(sub)
            continue
        for slot in sorted(sub.iterdir(), key=lambda p: p.name.lower()):
            if slot.is_dir() and _sorted_images(slot):   # Dia_X/slot_N (nivel 2)
                found.append(slot)
    return found


# ---------------------------------------------------------------------------
# Listas
# ---------------------------------------------------------------------------

def lists_summary(data=None) -> list:
    data = data if data is not None else load()
    return [
        (l["id"], l.get("name", "?"), len(l.get("items", [])))
        for l in data.get("lists", [])
    ]


def get_active(data=None) -> str:
    data = data if data is not None else load()
    ids = [l["id"] for l in data.get("lists", [])]
    active = data.get("active", "")
    if active in ids:
        return active
    return ids[0] if ids else ""


def set_active(list_id: str) -> None:
    data = load()
    data["active"] = list_id
    save(data)


def get_list(list_id: str, data=None):
    data = data if data is not None else load()
    for l in data.get("lists", []):
        if l["id"] == list_id:
            return l
    return None


def find_list_by_name(name: str, data=None):
    data = data if data is not None else load()
    for l in data.get("lists", []):
        if l.get("name") == name:
            return l
    return None


def read_caption(folder) -> str:
    """Le a legenda (Legenda.txt) de uma pasta de publicacao, se existir."""
    folder = Path(folder)
    for name in ("Legenda.txt", "legenda.txt"):
        p = folder / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    return ""


def new_item(src_path, folder_label, hashes_hex, meta=None,
             duplicate=False, dup_location="", dup_locations=None) -> dict:
    """Constroi (sem salvar) o dict de um item, para import em lote."""
    src = Path(src_path)
    imgs = _sorted_images(src)
    thumb = str(imgs[0]) if imgs else ""
    default_meta = {"views": "N/D", "likes": "N/D", "comments": "N/D", "post_date": "N/D"}
    locs = list(dup_locations) if dup_locations else ([dup_location] if dup_location else [])
    return {
        "id": uuid.uuid4().hex,
        "src_path": str(src),
        "folder": folder_label,
        "thumbnail": thumb,
        "caption": read_caption(src),
        "hashes": list(hashes_hex),
        "n_images": len(imgs),
        "used": False,
        "duplicate": bool(duplicate),
        "dup_location": dup_location,   # primeira ocorrencia (compat/exibicao)
        "dup_locations": locs,          # TODAS as pastas onde ja existe
        "meta": {**default_meta, **(meta or {})},
    }


def create_list_with_items(name: str, items: list) -> str:
    data = load()
    list_id = uuid.uuid4().hex
    data.setdefault("lists", []).append({
        "id": list_id,
        "name": name or "Sem nome",
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "items": list(items),
    })
    data["active"] = list_id
    save(data)
    return list_id


def delete_list(list_id: str) -> None:
    data = load()
    data["lists"] = [l for l in data.get("lists", []) if l["id"] != list_id]
    if data.get("active") == list_id:
        data["active"] = data["lists"][0]["id"] if data["lists"] else ""
    save(data)


# ---------------------------------------------------------------------------
# Itens
# ---------------------------------------------------------------------------

def find_item(list_id, item_id, data=None):
    l = get_list(list_id, data)
    if l is None:
        return None
    for it in l.get("items", []):
        if it["id"] == item_id:
            return it
    return None


def item_images(item: dict) -> list:
    return _sorted_images(Path(item.get("src_path", "")))


def set_item_field(list_id, item_id, field, value) -> None:
    data = load()
    it = find_item(list_id, item_id, data)
    if it is not None:
        it[field] = value
        save(data)


def remove_item(list_id, item_id) -> None:
    """Remove o item da lista (NAO apaga as imagens — elas sao da conta de origem)."""
    data = load()
    l = get_list(list_id, data)
    if l is None:
        return
    l["items"] = [it for it in l.get("items", []) if it["id"] != item_id]
    save(data)


# ---------------------------------------------------------------------------
# Filtros e ordenacao (logica pura — a UI so passa os parametros)
# ---------------------------------------------------------------------------

_DAY_RE = re.compile(r"[Dd][Ii][Aa]\s*_?\s*(\d+)")


def day_number(item: dict):
    """Numero do dia extraido do rotulo da pasta ('Dia20_...' → 20). None se nao tiver."""
    m = _DAY_RE.search(item.get("folder") or "")
    return int(m.group(1)) if m else None


def _norm(s: str) -> str:
    """Minusculas sem acentos, para comparacoes tolerantes (Comentar/COMENTAR/coménta...)."""
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def item_status(item: dict) -> str:
    """'used' | 'duplicate' | 'available' (used tem prioridade sobre duplicate)."""
    if item.get("used"):
        return "used"
    if item.get("duplicate"):
        return "duplicate"
    return "available"


_CTA_ORDER = ["comentar", "seguir", "guardar", "link na bio"]


def cta_sort_key(item: dict) -> tuple:
    """Ordena por tipo de CTA (Comentar primeiro); sem CTA/pendentes por ultimo."""
    c = _norm(item.get("cta") or "")
    if not c or "nao detectada" in c or "indisponivel" in c:
        return (len(_CTA_ORDER) + 1, "")
    for i, t in enumerate(_CTA_ORDER):
        if t in c:
            return (i, c)
    return (len(_CTA_ORDER), c)


def filter_items(items: list, status: str = "all", cta: str = "all",
                 trigger: str = "", day_min=None, day_max=None) -> list:
    """Filtro combinavel (todas as condicoes valem ao mesmo tempo).

    status : all | available | duplicate | used
    cta    : all | none | trecho normalizado ('comentar', 'guardar', 'seguir', 'link na bio')
    trigger: palavra-gatilho contida no CTA (ex.: 'RECETAS' acha 'Comentar RECETAS')
    day_min/day_max: faixa do numero do dia (itens sem 'Dia N' ficam fora se houver faixa)
    """
    out = []
    trig = _norm(trigger.strip()) if trigger else ""
    for it in items:
        if status != "all" and item_status(it) != status:
            continue
        c = _norm(it.get("cta") or "")
        if cta == "none":
            if c and "nao detectada" not in c and "indisponivel" not in c:
                continue
        elif cta != "all":
            if cta not in c:
                continue
        if trig and trig not in c:
            continue
        if day_min is not None or day_max is not None:
            d = day_number(it)
            if d is None:
                continue
            if day_min is not None and d < day_min:
                continue
            if day_max is not None and d > day_max:
                continue
        out.append(it)
    return out


def sort_items(items: list, mode: str = "orig") -> list:
    """Ordenacao estavel: empates preservam a ordem original da lista.

    mode: orig | day_asc | day_desc | avail_first | gray_first | cta
    """
    if mode in ("day_asc", "day_desc"):
        rev = (mode == "day_desc")
        with_day = [it for it in items if day_number(it) is not None]
        without = [it for it in items if day_number(it) is None]
        with_day.sort(key=day_number, reverse=rev)
        return with_day + without
    if mode == "avail_first":
        order = {"available": 0, "duplicate": 1, "used": 2}
        return sorted(items, key=lambda it: order[item_status(it)])
    if mode == "gray_first":
        order = {"available": 1, "duplicate": 0, "used": 0}
        return sorted(items, key=lambda it: order[item_status(it)])
    if mode == "cta":
        return sorted(items, key=cta_sort_key)
    return list(items)
