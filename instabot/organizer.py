import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

# Aceita todas as combinacoes de nome:
#   Dia24_16_06_26_V  (contador + data + inicial)
#   Dia24_16_06_26    (contador + data)
#   16_06_26_V        (data + inicial)
#   16_06_26          (so data)
# Grupos: 1=contador(opt) 2=DD 3=MM 4=AA 5=inicial(opt)
DIA_FOLDER_RE = re.compile(
    r"^(?:Dia(\d+)_)?(\d{2})_(\d{2})_(\d{2})(?:_([A-Za-z]+))?$"
)


def today_date_str() -> str:
    return date.today().strftime("%d_%m_%y")


def find_existing_dia_folder(
    db_folder: Path,
    date_str: str,
    initial: str,
    include_day_counter: bool = True,
    include_person_initial: bool = True,
) -> Optional[Path]:
    for entry in db_folder.iterdir():
        if not entry.is_dir():
            continue
        m = DIA_FOLDER_RE.match(entry.name)
        if not m:
            continue
        entry_date = f"{m.group(2)}_{m.group(3)}_{m.group(4)}"
        if entry_date != date_str:
            continue
        has_counter = m.group(1) is not None
        if has_counter != include_day_counter:
            continue
        entry_initial = m.group(5) or ""
        has_initial = bool(entry_initial)
        if has_initial != include_person_initial:
            continue
        if include_person_initial and entry_initial.upper() != initial.upper():
            continue
        return entry
    return None


def next_dia_number(db_folder: Path) -> int:
    max_n = 0
    for entry in db_folder.iterdir():
        if not entry.is_dir():
            continue
        m = DIA_FOLDER_RE.match(entry.name)
        if m and m.group(1) is not None:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def set_large_icons_view(folder: Path) -> None:
    """Faz a pasta abrir em modo 'Icones Grandes' no Explorer."""
    desktop_ini = folder / "desktop.ini"
    if not desktop_ini.exists():
        desktop_ini.write_text("[.ShellClassInfo]\nFolderType=Pictures\n", encoding="utf-8")
        subprocess.run(["attrib", "+h", "+s", str(desktop_ini)], check=False)
    subprocess.run(["attrib", "+r", str(folder)], check=False)


def ensure_day_folder(
    db_folder: Path,
    initial: str,
    slots: int = 6,
    include_day_counter: bool = True,
    include_person_initial: bool = True,
) -> Path:
    """Garante que a pasta do dia de hoje exista com as N subpastas numeradas e Legenda.txt."""
    date_str = today_date_str()
    existing = find_existing_dia_folder(
        db_folder, date_str, initial, include_day_counter, include_person_initial
    )
    if existing:
        return existing

    parts = [date_str]
    if include_day_counter:
        dia_num = next_dia_number(db_folder)
        parts.insert(0, f"Dia{dia_num}")
    if include_person_initial and initial:
        parts.append(initial.upper())

    folder_name = "_".join(parts)
    day_folder = db_folder / folder_name
    day_folder.mkdir(parents=True, exist_ok=False)

    for i in range(1, slots + 1):
        slot = day_folder / str(i)
        slot.mkdir()
        (slot / "Legenda.txt").write_text("", encoding="utf-8")
        set_large_icons_view(slot)

    set_large_icons_view(day_folder)
    return day_folder


def find_next_empty_slot(day_folder: Path, slots: int = 6) -> Optional[Path]:
    """Retorna a primeira subpasta (1..slots) que ainda nao tem midia."""
    for i in range(1, slots + 1):
        slot = day_folder / str(i)
        if not slot.exists():
            slot.mkdir()
            (slot / "Legenda.txt").write_text("", encoding="utf-8")
            set_large_icons_view(slot)
            return slot
        media_files = [
            f for f in slot.iterdir()
            if f.name.lower() not in ("legenda.txt", "desktop.ini", ".hashes.json")
        ]
        if not media_files:
            return slot
    return None


def save_media_to_slot(slot: Path, media_paths: list[Path]) -> list[Path]:
    """Copia as midias para a subpasta, renomeando em ordem: 1, 2, 3...
    Apos salvar, dispara o cache de hashes via dedup para que proximas
    comparacoes carreguem do arquivo em vez de reprocessar as imagens."""
    saved = []
    for idx, src in enumerate(media_paths, start=1):
        ext = src.suffix
        dest = slot / f"{idx}{ext}"
        dest.write_bytes(src.read_bytes())
        saved.append(dest)
    set_large_icons_view(slot)

    try:
        import dedup
        dedup.get_all_hashes(slot)
    except Exception:
        pass

    return saved
