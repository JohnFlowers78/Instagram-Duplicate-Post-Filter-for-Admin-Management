"""Motor de Postagem/Programação (o 'cérebro' — sem tocar no Instagram).

Regras de horário (definidas pelo usuário):
- 8 horários-base por dia: 00, 03, 06, 09, 12, 15, 18, 21.
- Cada base tem 5 variantes: hora cheia -10, -5, 0, +5, +10 min.
  (Ex.: base 00h → 23:50, 23:55, 00:00, 00:05, 00:10 — o -10/-5 caem no dia anterior.)
- 'Variância' opcional (0/20/30/40 min) desloca TODAS as variantes para a frente.
- Ao PROGRAMAR: cada publicação AGENDADA sorteia 1 das 5 variantes do seu horário-base,
  evitando repetir a MESMA variante 3 vezes seguidas. Publicações IMEDIATAS vão para 'agora'.

Este modulo so calcula e armazena (post_plan.json). Quem posta de fato e o poster.py.
100% testavel isolado.
"""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from paths import DATA_DIR

PLAN_FILE = DATA_DIR / "post_plan.json"

BASE_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]
VARIANT_OFFSETS = [-10, -5, 0, 5, 10]     # minutos em torno da hora cheia
VARIANCE_OPTIONS = [0, 20, 30, 40]


# ---------------------------------------------------------------------------
# Calculo de horarios
# ---------------------------------------------------------------------------

def variant_times(target_date: date, base_hour: int, variance: int = 0) -> list:
    """Os 5 datetimes possiveis de um horario-base num dia (com variancia)."""
    base = datetime(target_date.year, target_date.month, target_date.day, base_hour, 0)
    return [base + timedelta(minutes=off + variance) for off in VARIANT_OFFSETS]


def choose_variant_indices(n: int, rnd: random.Random = None) -> list:
    """n indices em 0..4, aleatorios, SEM repetir o mesmo 3 vezes seguidas."""
    rnd = rnd or random.Random()
    picks = []
    for _ in range(n):
        choices = list(range(len(VARIANT_OFFSETS)))
        if len(picks) >= 2 and picks[-1] == picks[-2]:
            choices = [c for c in choices if c != picks[-1]]  # barra o 3o igual
        picks.append(rnd.choice(choices))
    return picks


def assign_scheduled_times(base_hours: list, variance: int = 0,
                           target_date: date = None, rnd: random.Random = None) -> list:
    """Para uma lista ORDENADA de horarios-base, devolve (datetime, variant_idx)
    de cada um — sorteando a variante e evitando 3 iguais seguidas."""
    target_date = target_date or date.today()
    idxs = choose_variant_indices(len(base_hours), rnd)
    out = []
    for bh, vi in zip(base_hours, idxs):
        out.append((variant_times(target_date, bh, variance)[vi], vi))
    return out


# ---------------------------------------------------------------------------
# Armazenamento (post_plan.json)
# ---------------------------------------------------------------------------

def load() -> dict:
    if PLAN_FILE.exists():
        try:
            data = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("tags", [])
                data.setdefault("days", {})
                return data
        except Exception:
            pass
    return {"tags": [], "days": {}}


def save(data: dict) -> None:
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# --- Contas @ salvas (marcacao de colaboradores) ---

def _norm_tag(handle: str) -> str:
    h = (handle or "").strip().lstrip("@")
    return f"@{h}" if h else ""


def get_tags() -> list:
    return load().get("tags", [])


def add_tag(handle: str) -> None:
    h = _norm_tag(handle)
    if not h:
        return
    data = load()
    if h not in data["tags"]:
        data["tags"].append(h)
        save(data)


def remove_tag(handle: str) -> None:
    data = load()
    data["tags"] = [t for t in data.get("tags", []) if t != _norm_tag(handle)]
    save(data)


# --- Config por dia / por publicacao ---

def _day(data: dict, day_key: str) -> dict:
    return data["days"].setdefault(
        day_key, {"variance": 0, "order": [], "posts": {}})


def get_day(day_key: str, data=None) -> dict:
    data = data if data is not None else load()
    return _day(data, day_key)


def set_variance(day_key: str, variance: int) -> None:
    data = load()
    _day(data, day_key)["variance"] = int(variance)
    save(data)


def set_order(day_key: str, ids: list) -> None:
    data = load()
    _day(data, day_key)["order"] = list(ids)
    save(data)


def set_post(day_key: str, entry_id: str, **fields) -> None:
    """Atualiza a config de uma publicacao. Campos: base_hour, mode
    ('immediate'|'scheduled'), tagged (list), music (str)."""
    data = load()
    day = _day(data, day_key)
    post = day["posts"].setdefault(entry_id, {
        "base_hour": None, "mode": "scheduled", "tagged": [],
        "music": "", "time": "", "status": "idle", "log": "",
    })
    for k in ("base_hour", "mode", "tagged", "music"):
        if k in fields:
            post[k] = fields[k]
    if entry_id not in day["order"]:
        day["order"].append(entry_id)
    save(data)


def program_day(day_key: str, target_date: date = None, rnd: random.Random = None) -> list:
    """Aplica a estrategia: agendadas recebem horario sorteado (na ORDEM da lista,
    sem 3 variantes iguais seguidas); imediatas vao para 'agora'. Marca status
    'scheduled'. Retorna [(entry_id, datetime, mode)] do que foi programado."""
    data = load()
    day = _day(data, day_key)
    variance = day.get("variance", 0)
    order = [eid for eid in day.get("order", []) if eid in day["posts"]]

    scheduled_ids = [eid for eid in order
                     if day["posts"][eid].get("mode") == "scheduled"
                     and day["posts"][eid].get("base_hour") is not None]
    base_hours = [day["posts"][eid]["base_hour"] for eid in scheduled_ids]
    times = assign_scheduled_times(base_hours, variance, target_date, rnd)

    result = []
    now = datetime.now()
    ti = 0
    for eid in order:
        post = day["posts"][eid]
        if post.get("mode") == "immediate":
            post["time"] = now.isoformat(timespec="minutes")
            post["status"] = "scheduled"
            result.append((eid, now, "immediate"))
        elif post.get("mode") == "scheduled" and post.get("base_hour") is not None:
            dt, _vi = times[ti]
            ti += 1
            post["time"] = dt.isoformat(timespec="minutes")
            post["status"] = "scheduled"
            result.append((eid, dt, "scheduled"))
    save(data)
    return result


def due_posts(now: datetime = None) -> list:
    """Publicacoes com status 'scheduled' cujo horario ja chegou.
    Retorna [(day_key, entry_id, post)]."""
    now = now or datetime.now()
    data = load()
    out = []
    for day_key, day in data.get("days", {}).items():
        for eid, post in day.get("posts", {}).items():
            if post.get("status") != "scheduled":
                continue
            t = post.get("time", "")
            try:
                dt = datetime.fromisoformat(t)
            except (ValueError, TypeError):
                continue
            if dt <= now:
                out.append((day_key, eid, post))
    out.sort(key=lambda x: x[2].get("time", ""))
    return out


def mark(day_key: str, entry_id: str, status: str, log_line: str = "") -> None:
    """status: idle|scheduled|posting|posted|failed."""
    data = load()
    day = _day(data, day_key)
    post = day.get("posts", {}).get(entry_id)
    if post is None:
        return
    post["status"] = status
    if log_line:
        stamp = datetime.now().strftime("%d/%m %H:%M")
        post["log"] = (post.get("log", "") + f"[{stamp}] {log_line}\n")[-2000:]
    save(data)
