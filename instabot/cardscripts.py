"""Perfis de script do modulo 'Edicao CARDs Finais'.

Cada PERFIL e uma forma salva de pedir um card final (e/ou legenda) ao ChatGPT:
  {id, name, cover_title, script, example_image, created}

- name        : nome do botao (ex.: "Comentar RECETAS v2")
- cover_title : titulo de capa que lembra o TIPO (ex.: "CTA Comentar",
                "Cliente Valter", "Troca de Gatilho", "Edicao Completa") — livre
- script      : o texto que instrui o ChatGPT (caixa media)
- example_image: caminho de UMA imagem-exemplo (copiada para card_scripts_media/)

Perfis viram botoes reutilizaveis (nome + miniatura). Persistido em
card_scripts.json (dentro de DATA_DIR). NADA aqui fala com o ChatGPT — isso e o
chatgpt.py; este modulo e so armazenamento (100% testavel isolado).
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from paths import DATA_DIR

CARDS_FILE = DATA_DIR / "card_scripts.json"
CARDS_MEDIA = DATA_DIR / "card_scripts_media"     # imagens-exemplo dos perfis
GEN_DIR = DATA_DIR / "cards_gerados"              # imagens geradas pelo ChatGPT

# Sugestoes de titulo de capa (o campo e livre — pode digitar qualquer um)
COVER_SUGGESTIONS = [
    "CTA Comentar", "CTA Guardar", "Cliente Valter",
    "Troca de Gatilho", "Edicao Completa",
]

# Dois exemplos-base fixos de referencia (o usuario pode trocar depois).
# Guardados como texto de apoio para colar no inicio dos scripts.
DEFAULT_BASE_EXAMPLES = (
    "Exemplo-base 1: card final com fundo escuro, CTA 'Comentá RECETAS' + 'Seguí'.\n"
    "Exemplo-base 2: card final vitrine, CTA 'Guardá' + 'Seguí', paleta clara."
)

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def load() -> dict:
    if CARDS_FILE.exists():
        try:
            data = json.loads(CARDS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "profiles" in data:
                return data
        except Exception:
            pass
    return {"profiles": [], "base_examples": DEFAULT_BASE_EXAMPLES}


def save(data: dict) -> None:
    CARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CARDS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def profiles() -> list:
    return load().get("profiles", [])


def get_profile(pid: str, data=None):
    data = data if data is not None else load()
    for p in data.get("profiles", []):
        if p.get("id") == pid:
            return p
    return None


def _copy_example(pid: str, src_path: str) -> str:
    """Copia a imagem-exemplo para card_scripts_media/<pid>.<ext>. '' se nao houver."""
    if not src_path:
        return ""
    src = Path(src_path)
    if not src.is_file() or src.suffix.lower() not in IMG_EXTS:
        return ""
    CARDS_MEDIA.mkdir(parents=True, exist_ok=True)
    dest = CARDS_MEDIA / f"{pid}{src.suffix.lower()}"
    try:
        # remove versao anterior (extensao pode mudar)
        for old in CARDS_MEDIA.glob(f"{pid}.*"):
            old.unlink(missing_ok=True)
        dest.write_bytes(src.read_bytes())
        return str(dest)
    except OSError:
        return ""


def create_profile(name: str, cover_title: str = "", script: str = "",
                   example_image_src: str = "") -> dict:
    data = load()
    pid = uuid.uuid4().hex
    prof = {
        "id": pid,
        "name": (name or "Sem nome").strip(),
        "cover_title": (cover_title or "").strip(),
        "script": script or "",
        "example_image": _copy_example(pid, example_image_src),
        "created": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    data.setdefault("profiles", []).append(prof)
    save(data)
    return prof


def update_profile(pid: str, name=None, cover_title=None, script=None,
                   example_image_src=None) -> None:
    data = load()
    p = get_profile(pid, data)
    if p is None:
        return
    if name is not None:
        p["name"] = name.strip() or p["name"]
    if cover_title is not None:
        p["cover_title"] = cover_title.strip()
    if script is not None:
        p["script"] = script
    if example_image_src is not None and example_image_src:
        p["example_image"] = _copy_example(pid, example_image_src)
    save(data)


def delete_profile(pid: str) -> None:
    data = load()
    data["profiles"] = [p for p in data.get("profiles", []) if p.get("id") != pid]
    save(data)
    try:
        for old in CARDS_MEDIA.glob(f"{pid}.*"):
            old.unlink(missing_ok=True)
    except OSError:
        pass


def get_base_examples() -> str:
    return load().get("base_examples", DEFAULT_BASE_EXAMPLES)


def set_base_examples(text: str) -> None:
    data = load()
    data["base_examples"] = text or ""
    save(data)


def gen_dir() -> Path:
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    return GEN_DIR
