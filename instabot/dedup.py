from pathlib import Path
from typing import Optional

from PIL import Image
import imagehash

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Quantas imagens iniciais do carrossel sao usadas para comparar publicacoes.
# O(s) CARD(s) final(is) variam entre publicacoes (mesmo quando o conteudo e o
# mesmo), por isso so as primeiras N imagens (o "miolo" do carrossel) entram
# na comparacao.
COMPARE_FIRST_N = 4


def hash_image(path: Path) -> Optional[imagehash.ImageHash]:
    try:
        with Image.open(path) as img:
            return imagehash.phash(img)
    except Exception:
        return None


def _sorted_numbered_images(folder: Path) -> list[Path]:
    """Retorna as imagens '1.jpg', '2.png', ... de uma pasta, em ordem numerica."""
    files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in IMG_EXTS and f.stem.isdigit():
            files.append(f)
    files.sort(key=lambda f: int(f.stem))
    return files


def get_first_n_hashes(folder: Path, n: int = COMPARE_FIRST_N) -> list[imagehash.ImageHash]:
    """Hashes das primeiras n imagens (em ordem) de uma pasta de publicacao."""
    hashes = []
    for f in _sorted_numbered_images(folder)[:n]:
        h = hash_image(f)
        if h is not None:
            hashes.append(h)
    return hashes


def hash_new_media(media_paths: list[Path], n: int = COMPARE_FIRST_N) -> list[imagehash.ImageHash]:
    """Hashes das primeiras n imagens recem-baixadas (assume que ja estao em ordem)."""
    hashes = []
    for path in media_paths:
        if path.suffix.lower() not in IMG_EXTS:
            continue
        h = hash_image(path)
        if h is not None:
            hashes.append(h)
        if len(hashes) >= n:
            break
    return hashes


def build_post_index(db_folder: Path, n: int = COMPARE_FIRST_N) -> list[tuple[Path, list[imagehash.ImageHash]]]:
    """Varre db_folder em busca de subpastas numeradas (1..6) que ja tem midia,
    e monta o indice de hashes das primeiras n imagens de cada uma."""
    index = []
    for slot_folder in db_folder.glob("*/*"):
        if not slot_folder.is_dir() or not slot_folder.name.isdigit():
            continue
        hashes = get_first_n_hashes(slot_folder, n)
        if hashes:
            index.append((slot_folder, hashes))
    return index


def find_duplicate_post(
    new_hashes: list[imagehash.ImageHash],
    post_index: list[tuple[Path, list[imagehash.ImageHash]]],
    threshold: int = 5,
) -> Optional[tuple[Path, int]]:
    """Compara as primeiras imagens da nova publicacao com as publicacoes ja
    enviadas. Retorna (pasta_existente, distancia_maxima) se for repetida,
    ou None se nao houver repeticao.
    """
    if not new_hashes:
        return None

    for existing_folder, existing_hashes in post_index:
        n = min(len(new_hashes), len(existing_hashes))
        if n == 0:
            continue
        distances = [new_hashes[i] - existing_hashes[i] for i in range(n)]
        if all(d <= threshold for d in distances):
            return existing_folder, max(distances)

    return None
