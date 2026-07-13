"""Deteccao do tipo de CTA (chamada pra acao) dos cards finais de um carrossel.

Estrategia: OCR (Tesseract) nos ultimos cards + classificacao por palavras-chave.
- Le so os ultimos N cards (onde ficam os cards finais).
- Junta todos os CTAs encontrados; prioridade sempre pra COMENTAR.
- Captura o gatilho do comentario (ex.: "Comenta QUIERO" -> QUIERO).

Degrada com elegancia: se o Tesseract/pytesseract nao estiverem disponiveis,
available() retorna False e o app segue funcionando (sem CTA).
"""

import re
import shutil
from pathlib import Path

# Caminhos comuns do tesseract.exe no Windows (o instalador oferece o de AppData;
# o usuario instalou em Program Files).
_TESS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    str(Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
]

LAST_N = 3            # quantos cards finais analisar
LANG = "por+spa"      # idiomas dos cards (portugues + espanhol)

_state = {"checked": False, "pt": None}


def _get_pt():
    if _state["checked"]:
        return _state["pt"]
    _state["checked"] = True
    try:
        import pytesseract
        cmd = shutil.which("tesseract")
        if not cmd:
            for p in _TESS_PATHS:
                if Path(p).is_file():
                    cmd = p
                    break
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        pytesseract.get_tesseract_version()  # valida a instalacao
        _state["pt"] = pytesseract
    except Exception:
        _state["pt"] = None
    return _state["pt"]


def available() -> bool:
    return _get_pt() is not None


def _ocr(image_paths) -> str:
    pt = _get_pt()
    if pt is None:
        return ""
    from PIL import Image
    parts = []
    for p in image_paths:
        for lang in (LANG, None):   # tenta por+spa; se faltar o pack, cai pro default
            try:
                with Image.open(p) as img:
                    parts.append(pt.image_to_string(img, lang=lang) if lang
                                 else pt.image_to_string(img))
                break
            except Exception:
                continue
    return "\n".join(parts)


_RE_COMMENT = re.compile(r"coment[ae]", re.I)
_RE_SAVE    = re.compile(r"guard|salv", re.I)
_RE_FOLLOW  = re.compile(r"seg[uú][ei]|sigue|s[ií]gue|follow|segu[ií]", re.I)
_RE_BIO     = re.compile(r"\bbio\b|link.{0,12}bio|enlace", re.I)
_RE_TRIGGER = re.compile(
    r"coment[ae]\w*\s+[\"“'']?([A-Za-zÁÉÍÓÚÑÜáéíóúñü]{3,})", re.I
)

_ORDER = ["Comentar", "Seguir", "Guardar", "Link na bio"]


def classify(text: str) -> dict:
    types = []
    trigger = ""
    if _RE_COMMENT.search(text):
        types.append("Comentar")
        m = _RE_TRIGGER.search(text)
        if m:
            trigger = m.group(1).upper()
    if _RE_FOLLOW.search(text):
        types.append("Seguir")
    if _RE_SAVE.search(text):
        types.append("Guardar")
    if _RE_BIO.search(text):
        types.append("Link na bio")
    return {"types": types, "trigger": trigger}


def format_cta(result: dict) -> str:
    types = sorted(set(result.get("types", [])),
                   key=lambda t: _ORDER.index(t) if t in _ORDER else 99)
    if not types:
        return "não detectada"
    parts = []
    for t in types:
        if t == "Comentar" and result.get("trigger"):
            parts.append(f"Comentar {result['trigger']}")
        else:
            parts.append(t)
    return " · ".join(parts)


def detect_cta(image_paths, last_n: int = LAST_N) -> str:
    """Le os ultimos cards e retorna a CTA formatada (ex.: 'Comentar QUIERO · Seguir').

    Retorna 'não detectada' se nao achar CTA. (Assume OCR disponivel — quem chama
    deve checar available() antes, pra decidir se roda o processo.)
    """
    imgs = list(image_paths)[-last_n:]
    return format_cta(classify(_ocr(imgs)))
