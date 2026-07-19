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


def _folder_signature(files: list[Path]) -> dict:
    """Assinatura das imagens da pasta: {nome: [tamanho, mtime_ns]}."""
    sig = {}
    for f in files:
        try:
            st = f.stat()
            sig[f.name] = [st.st_size, st.st_mtime_ns]
        except OSError:
            sig[f.name] = [0, 0]
    return sig


def get_all_hashes(folder: Path) -> list[imagehash.ImageHash]:
    """Hashes de TODAS as imagens de uma pasta, com cache em .hashes.json.

    O cache guarda a assinatura (nome, tamanho e data de modificacao) de cada
    imagem: se QUALQUER arquivo for trocado — ex.: Card Final refeito por IA —
    a assinatura muda e os hashes sao recalculados sozinhos. Caches no formato
    antigo (lista simples, sem assinatura) tambem sao recomputados.
    """
    files = _sorted_numbered_images(folder)
    cache_file = folder / _HASH_CACHE
    if not files:
        cache_file.unlink(missing_ok=True)  # pasta sem imagens: cache orfao
        return []

    sig = _folder_signature(files)
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if (
                isinstance(data, dict)
                and data.get("files") == sig
                and isinstance(data.get("hashes"), list)
                and data["hashes"]
            ):
                return [imagehash.hex_to_hash(h) for h in data["hashes"]]
            # assinatura diferente ou formato antigo → recomputa e sobrescreve
        except Exception:
            pass

    hashes = []
    for f in files:
        h = hash_image(f)
        if h is not None:
            hashes.append(h)

    if hashes:
        try:
            cache_file.write_text(
                json.dumps({"files": sig, "hashes": [str(h) for h in hashes]}),
                encoding="utf-8",
            )
        except Exception:
            pass

    return hashes


def is_duplicate_pair(
    ha: list[imagehash.ImageHash],
    hb: list[imagehash.ImageHash],
    threshold: int = 5,
    cta_cards: int = 2,
    threshold_loose: int = 16,
) -> bool:
    """As mesmas 2 regras do find_duplicate_post, para um par avulso (simetrico)."""
    if not ha or not hb:
        return False
    needed = max(1, min(len(ha), len(hb)) - 1)
    matched, _, _ = _match_stats(ha, hb, threshold)
    if matched >= needed:
        return True
    ok, _ = content_match(ha, hb, threshold_loose, cta_cards)
    return ok


def find_all_duplicates(
    new_hashes: list[imagehash.ImageHash],
    post_index: list[tuple[Path, list[imagehash.ImageHash]]],
    threshold: int = 5,
    cta_cards: int = 2,
    threshold_loose: int = 16,
) -> list[Path]:
    """TODAS as pastas onde a publicacao ja existe (nao para na primeira).
    Usado para o 'REPETIDAS: X' com a lista de diretorios de cada carrossel."""
    if not new_hashes:
        return []
    return [
        folder for folder, hashes in post_index
        if hashes and is_duplicate_pair(new_hashes, hashes,
                                        threshold, cta_cards, threshold_loose)
    ]


def audit_duplicates(
    db_folder: Path,
    threshold: int = 5,
    cta_cards: int = 2,
    threshold_loose: int = 16,
    progress_cb=None,
) -> list[list[Path]]:
    """AUDITORIA: compara a Pasta de Destino com ela mesma e devolve os GRUPOS
    de publicacoes repetidas (2, 3, N copias — sem limite por grupo).

    Usa as mesmas 2 regras dos filtros (classica + miolo) e uniao-busca para
    agrupar: se A==B e B==C, o grupo e {A, B, C}. progress_cb(i, n) por linha.
    """
    index = build_post_index(db_folder)
    n = len(index)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        if progress_cb:
            progress_cb(i + 1, n)
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue   # ja estao no mesmo grupo
            if is_duplicate_pair(index[i][1], index[j][1],
                                 threshold, cta_cards, threshold_loose):
                union(i, j)

    groups: dict = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(index[i][0])
    out = [sorted(g, key=lambda p: str(p).lower()) for g in groups.values() if len(g) > 1]
    out.sort(key=lambda g: (-len(g), str(g[0]).lower()))
    return out


def purge_hash_caches(root: Path) -> int:
    """Apaga TODOS os .hashes.json dentro de root (recursivo).

    Usar depois de trocar muitos Cards Finais: os hashes de todas as pastas
    serao recalculados a partir das imagens reais na proxima comparacao.
    Retorna quantos arquivos foram apagados.
    """
    count = 0
    for f in Path(root).rglob(_HASH_CACHE):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count


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
    """Varre db_folder e monta o indice de hashes de cada publicacao.

    Aceita QUALQUER subpasta de 2o nivel que contenha imagens numeradas — nao
    apenas nomes puramente numericos. Isso inclui slots renomeados na mao
    ('7 - Vitrine', '10 - Híbrido') e pastas de colecao: tudo que esta na Pasta
    de Destino e conteudo reivindicado e DEVE bloquear repeticoes."""
    index = []
    for slot_folder in db_folder.glob("*/*"):
        if not slot_folder.is_dir():
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


def _trim_cta(hashes: list, cta_cards: int) -> list:
    """Remove os ultimos cta_cards (a CTA fica SEMPRE no fim do carrossel)."""
    if cta_cards > 0 and len(hashes) > cta_cards:
        return hashes[:-cta_cards]
    return hashes


def content_match(
    new_hashes: list[imagehash.ImageHash],
    hashes: list[imagehash.ImageHash],
    threshold_loose: int = 16,
    cta_cards: int = 2,
) -> tuple[bool, int]:
    """REGRA DO MIOLO: ignora os ultimos cta_cards de CADA lado e exige que TODO
    o miolo menor encontre par, com limiar tolerante.

    Por que existe (medido em caso real, 17/07/2026):
    - A CTA pode ser 1 OU 2 cards e e trocada/redesenhada entre republicacoes
      → ate 2 cards legitimamente diferentes no fim (a tolerancia de 1 nao basta).
    - O MESMO card baixado em epocas diferentes muda 6-14 bits no pHash
      (recompressao do SnapInsta/Instagram) — acima do limiar estrito 5.
    - Cards de publicacoes DIFERENTES ficam a 20+ bits.
    → limiar do miolo default 16: no meio do vao entre 14 (mesma arte) e 20 (outra arte).

    Falso positivo exigiria TODOS os cards do miolo (>=3) parecidos aos pares — na
    pratica nao ocorre entre artes diferentes. Retorna (e_repetida, dist_maxima).
    """
    a = _trim_cta(new_hashes, cta_cards)
    b = _trim_cta(hashes, cta_cards)
    needed = min(len(a), len(b))
    if needed < 3:   # miolo curto demais para evidencia coletiva confiavel
        return False, 0
    matched, max_dist, _ = _match_stats(a, b, threshold_loose)
    return matched >= needed, max_dist


def best_match_stats(
    new_hashes: list[imagehash.ImageHash],
    post_index: list[tuple[Path, list[imagehash.ImageHash]]],
    threshold: int = 5,
    cta_cards: int = 2,
    threshold_loose: int = 16,
) -> str:
    """Retorna string com o candidato mais proximo (para log de diagnostico)."""
    if not new_hashes:
        return "sem hashes novos"
    if not post_index:
        return "indice vazio"

    best = None

    for folder, hashes in post_index:
        if not hashes:
            continue
        matched, max_dist, min_sem_par = _match_stats(new_hashes, hashes, threshold)
        needed_full = min(len(new_hashes), len(hashes))
        needed = max(1, needed_full - 1)  # ultimo card (CTA) sempre muda
        name = f"{folder.parent.name}/{folder.name}"
        if best is None or matched > best[0]:
            best = (matched, max_dist, needed, name, min_sem_par, hashes)

    if best is None:
        return "nenhum candidato"
    matched, max_dist, needed, name, min_sem_par, bh = best
    s = f"mais proximo: {name} ({matched}/{needed} pares · dist max {max_dist})"
    if min_sem_par is not None:
        s += f" · sem par: dist {min_sem_par}"
    # diagnostico da regra do miolo para o mesmo candidato
    a2 = _trim_cta(new_hashes, cta_cards)
    b2 = _trim_cta(bh, cta_cards)
    n2 = min(len(a2), len(b2))
    m2, _, _ = _match_stats(a2, b2, threshold_loose)
    s += f" · miolo {m2}/{n2}@t{threshold_loose}"
    return s


def find_duplicate_post(
    new_hashes: list[imagehash.ImageHash],
    post_index: list[tuple[Path, list[imagehash.ImageHash]]],
    threshold: int = 5,
    cta_cards: int = 2,
    threshold_loose: int = 16,
) -> Optional[tuple[Path, int]]:
    """Jogo da memoria com matching bipartido maximo (resultado sempre otimo).

    Cada imagem existente so pode ser usada uma vez (bijetivo); augmenting paths
    garante o maior numero possivel de pares, independente da ordem dos cards.

    DUAS regras por candidato (qualquer uma marca REPETIDA):
    1. CLASSICA: com limiar estrito, todos os cards menos 1 encontram par
       (pega copias identicas e a troca de 1 card final).
    2. MIOLO (content_match): ignora os ultimos cta_cards de cada lado e exige o
       miolo inteiro pareado com limiar tolerante — pega CTA de 2 cards trocada
       E a recompressao entre downloads (ver medicao no docstring de content_match).

    Retorna (pasta_existente, distancia_maxima) se duplicada, None caso contrario.
    """
    if not new_hashes:
        return None

    for folder, hashes in post_index:
        if not hashes:
            continue
        needed_full = min(len(new_hashes), len(hashes))
        # Regra 1 — classica: o ultimo card (CTA) sempre muda — ignora 1
        needed = max(1, needed_full - 1)
        matched, max_dist, _ = _match_stats(new_hashes, hashes, threshold)
        if matched >= needed:
            return folder, max_dist
        # Regra 2 — miolo tolerante (CTA de ate cta_cards + recompressao)
        ok, mdist = content_match(new_hashes, hashes, threshold_loose, cta_cards)
        if ok:
            return folder, mdist

    return None
