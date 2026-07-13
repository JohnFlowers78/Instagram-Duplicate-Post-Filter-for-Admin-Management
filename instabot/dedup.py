import json
from pathlib import Path
from typing import Optional

from PIL import Image
import imagehash

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_HASH_CACHE = ".hashes.json"  # arquivo de cache dentro de cada slot


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


def get_all_hashes(folder: Path) -> list[imagehash.ImageHash]:
    """Hashes de TODAS as imagens de uma pasta, com cache em .hashes.json.

    Na primeira vez: computa via phash e salva o cache.
    Nas proximas vezes: carrega do cache instantaneamente (sem reabrir as imagens).
    O cache so fica desatualizado se as imagens forem trocadas manualmente — nesse
    caso basta apagar o arquivo .hashes.json dentro do slot para forcar recomputo.
    """
    cache_file = folder / _HASH_CACHE
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                actual = _sorted_numbered_images(folder)
                if not actual:
                    cache_file.unlink(missing_ok=True)  # Pasta sem imagens
                elif len(data) == len(actual):  # Cache completo e valido
                    return [imagehash.hex_to_hash(h) for h in data]
                # len(data) != len(actual): cache desatualizado → recomputa e sobrescreve
        except Exception:
            pass

    hashes = []
    for f in _sorted_numbered_images(folder):
        h = hash_image(f)
        if h is not None:
            hashes.append(h)

    if hashes:
        try:
            cache_file.write_text(
                json.dumps([str(h) for h in hashes]), encoding="utf-8"
            )
        except Exception:
            pass

    return hashes


def hashes_from_hex(hex_list) -> list[imagehash.ImageHash]:
    """Reconverte hashes salvos como hex (ex.: itens do Filtro Entre Contas)."""
    out = []
    for h in hex_list or []:
        try:
            out.append(imagehash.hex_to_hash(h))
        except Exception:
            pass
    return out


def hash_new_media(media_paths: list[Path]) -> list[imagehash.ImageHash]:
    """Hashes de todas as imagens recem-baixadas (assume que ja estao em ordem)."""
    hashes = []
    for path in media_paths:
        if path.suffix.lower() not in IMG_EXTS:
            continue
        h = hash_image(path)
        if h is not None:
            hashes.append(h)
    return hashes


def build_post_index(db_folder: Path) -> list[tuple[Path, list[imagehash.ImageHash]]]:
    """Varre db_folder em busca de subpastas numeradas que ja tem midia,
    e monta o indice de hashes de TODAS as imagens de cada publicacao."""
    index = []
    for slot_folder in db_folder.glob("*/*"):
        if not slot_folder.is_dir() or not slot_folder.name.isdigit():
            continue
        hashes = get_all_hashes(slot_folder)
        if hashes:
            index.append((slot_folder, hashes))
    return index


def _max_bipartite_matching(n_right: int, adj: list[list[int]]) -> tuple[int, list[int]]:
    """Matching bipartido maximo via augmenting paths (DFS).

    adj[u] = indices do lado direito que u pode parear.
    Retorna (tamanho_matching, match_r) onde match_r[v] = u pareado com v, -1 se livre.
    O resultado e sempre otimo — nao depende de ordem nem de escolha gulosa.
    """
    match_r = [-1] * n_right

    def augment(u: int, visited: set) -> bool:
        for v in adj[u]:
            if v not in visited:
                visited.add(v)
                if match_r[v] == -1 or augment(match_r[v], visited):
                    match_r[v] = u
                    return True
        return False

    total = 0
    for u in range(len(adj)):
        if augment(u, set()):
            total += 1
    return total, match_r


def _match_stats(
    new_hashes: list[imagehash.ImageHash],
    hashes: list[imagehash.ImageHash],
    threshold: int,
) -> tuple[int, int, Optional[int]]:
    """Retorna (matched, max_dist, min_dist_sem_par) usando matching bipartido maximo.

    min_dist_sem_par: menor distancia encontrada entre qualquer imagem nova sem par
    e qualquer imagem existente — indica o quanto o limiar precisaria aumentar para
    emparelhar a proxima imagem. None se todas as novas encontraram par.
    """
    adj = [
        [i for i, eh in enumerate(hashes) if int(nh - eh) <= threshold]
        for nh in new_hashes
    ]
    matched, match_r = _max_bipartite_matching(len(hashes), adj)

    matched_new: set[int] = {u for u in match_r if u >= 0}
    max_dist = 0
    for v, u in enumerate(match_r):
        if u >= 0:
            max_dist = max(max_dist, int(new_hashes[u] - hashes[v]))

    min_sem_par: Optional[int] = None
    for i, nh in enumerate(new_hashes):
        if i not in matched_new:
            for eh in hashes:
                d = int(nh - eh)
                if min_sem_par is None or d < min_sem_par:
                    min_sem_par = d

    return matched, max_dist, min_sem_par


def best_match_stats(
    new_hashes: list[imagehash.ImageHash],
    post_index: list[tuple[Path, list[imagehash.ImageHash]]],
    threshold: int = 5,
) -> str:
    """Retorna string com o candidato mais proximo (para log de diagnostico)."""
    if not new_hashes:
        return "sem hashes novos"
    if not post_index:
        return "indice vazio"

    best: Optional[tuple[int, int, int, str, Optional[int]]] = None

    for folder, hashes in post_index:
        if not hashes:
            continue
        matched, max_dist, min_sem_par = _match_stats(new_hashes, hashes, threshold)
        needed_full = min(len(new_hashes), len(hashes))
        needed = max(1, needed_full - 1)  # ultimo card (CTA) sempre muda
        name = f"{folder.parent.name}/{folder.name}"
        if best is None or matched > best[0]:
            best = (matched, max_dist, needed, name, min_sem_par)

    if best is None:
        return "nenhum candidato"
    matched, max_dist, needed, name, min_sem_par = best
    s = f"mais proximo: {name} ({matched}/{needed} pares · dist max {max_dist})"
    if min_sem_par is not None:
        s += f" · sem par: dist {min_sem_par}"
    return s


def find_duplicate_post(
    new_hashes: list[imagehash.ImageHash],
    post_index: list[tuple[Path, list[imagehash.ImageHash]]],
    threshold: int = 5,
) -> Optional[tuple[Path, int]]:
    """Jogo da memoria com matching bipartido maximo (resultado sempre otimo).

    Cada imagem existente so pode ser usada uma vez (bijetivo). Diferente de
    abordagens gulosas, o algoritmo de augmenting paths garante o maior numero
    possivel de pares — independente de qual imagem e processada primeiro.

    Regra de duplicata: o conjunto MENOR fica todo emparelhado.
    - Mesmo post, ordem diferente       → todos emparelhados → REPETIDA
    - Post novo com 2 cards extras      → existente emparelhado → REPETIDA
    - Posts que diferem no card final   → ambos ficam com 1 sem par → NAO REPETIDA

    Retorna (pasta_existente, distancia_maxima) se duplicada, None caso contrario.
    """
    if not new_hashes:
        return None

    for folder, hashes in post_index:
        if not hashes:
            continue
        needed_full = min(len(new_hashes), len(hashes))
        # O ultimo card (CTA) muda sempre entre publicacoes do mesmo perfil — ignora 1
        needed = max(1, needed_full - 1)
        matched, max_dist, _ = _match_stats(new_hashes, hashes, threshold)
        if matched >= needed:
            return folder, max_dist

    return None
