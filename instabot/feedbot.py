"""Coletor do Feed Especial ("Instagram Saudavel") — Fase 1 (MVP local).

Processo LOGICAMENTE separado do app: este modulo so escreve no inbox
(feedinbox). O app chama collect() numa thread hoje; na Fase 3 o mesmo
modulo roda sozinho numa VM (ver CLI no fim) — o contrato nao muda.

Comportamento:
- Usa um perfil de Chrome PROPRIO (DATA_DIR/feedbot_profile) — e a CONTA-ISCA,
  cujo algoritmo o usuario moldou para o nicho. NAO e o perfil do bot de trabalho.
- Rola o feed da conta-isca por N minutos, lendo cada publicacao visivel:
  shortcode, curtidas/comentarios (pt/es/en), capa, carrossel ou nao.
- Filtro: faixa de likes + piso de comentarios + so carrosseis (config do feed).
- "Jardineiro do algoritmo": demora mais nas publicacoes DENTRO do gosto e
  passa rapido pelas de fora — coleta e mantem o contexto da conta no mesmo gesto.
"""

import random
import re
import time
import uuid
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

import feedinbox
from downloader import _report, _wait_instagram_login
from paths import DATA_DIR

PROFILE_DIR = DATA_DIR / "feedbot_profile"   # conta-isca (separado do trabalho)

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/148.0 Safari/537.36")

# Contadores em pt/es/en: "24,3 mil curtidas", "2,4 mi", "1.234 Me gusta", "2.4K likes"
_LIKES_RE = re.compile(r"([\d.,]+\s*(?:mil|mi|k|m)?)\s*(?:curtida|me gusta|likes?|gosto)", re.I)
# Formato "Curtido por fulano e outras 24.301 pessoas" / "y 24.301 personas más"
# / "and 24,301 others" — muito comum no feed (era o furo que deixava tudo
# como "curtidas ocultas")
_LIKES_RE2 = re.compile(
    r"(?:outras?|y|and)\s+([\d.,]+\s*(?:mil|mi|k|m)?)\s*(?:pessoas|personas|others)", re.I)
_COMM_RE = re.compile(r"([\d.,]+\s*(?:mil|mi|k|m)?)\s*coment", re.I)


def parse_count(txt) -> "int | None":
    """'24,3 mil' → 24300 · '1.234' → 1234 · '2,4 mi'/'2.4M' → 2400000."""
    if not txt:
        return None
    t = str(txt).strip().lower().replace("\xa0", " ")
    m = re.match(r"([\d.,]+)\s*(mil|mi|k|m)?$", t)
    if not m:
        return None
    num, suf = m.group(1), (m.group(2) or "")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", num):     # 1.234.567 (separador de milhar)
        val = float(re.sub(r"[.,]", "", num))
    else:
        s = num.replace(",", ".")
        if s.count(".") > 1:
            val = float(re.sub(r"[^\d]", "", num))
        else:
            try:
                val = float(s)
            except ValueError:
                return None
    mult = {"mil": 1_000, "k": 1_000, "mi": 1_000_000, "m": 1_000_000}.get(suf, 1)
    return int(val * mult)


_EXTRACT_JS = """
() => {
  const out = [];
  for (const art of document.querySelectorAll('article')) {
    const r = art.getBoundingClientRect();
    if (r.bottom < -200 || r.top > innerHeight + 200) continue;   // so as visiveis
    // Fracao visivel: evita avaliar publicacao "espiando" na borda, com o
    // conteudo (contadores/carrossel) ainda nem montado pelo Instagram
    const inter = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
    const vis = inter / Math.min(Math.max(r.height, 1), innerHeight);
    // Resgate: post ja SUBINDO (topo cortado la em cima) mas com o RODAPE de
    // dados (contadores/legenda) ainda visivel — se nao pegar agora, o scroll
    // "come estrada" e perde a publicacao para sempre
    const dataVis = r.top < 0 && r.bottom > 120 && r.bottom <= innerHeight + 40;
    const link = art.querySelector('a[href*="/p/"]');
    if (!link) continue;
    const m = (link.getAttribute('href') || '').match(/\\/p\\/([^\\/\\?#]+)/);
    if (!m) continue;
    const isVideo = !!art.querySelector('video');
    const nextBtn = art.querySelector(
      'button[aria-label*="r\\u00f3xim"], button[aria-label*="van\\u00e7ar"], ' +
      'button[aria-label*="iguiente"], button[aria-label="Next"]');
    const slides = art.querySelectorAll('ul li img, div[role="presentation"] ul li').length;
    const imgIdx = !!art.querySelector('a[href*="img_index"]');
    // Capa REAL do post: o MAIOR <img> renderizado do card. (O primeiro <img>
    // do article e o avatar do autor — era o bug das capas erradas.)
    let bestImg = '', bestArea = 0;
    for (const im of art.querySelectorAll('img')) {
      const ir = im.getBoundingClientRect();
      const area = ir.width * ir.height;
      if (ir.width >= 80 && area > bestArea) {
        bestArea = area;
        bestImg = im.currentSrc || im.src || '';
      }
    }
    out.push({
      sc: m[1],
      img: bestImg,
      text: (art.innerText || '').slice(0, 1500),
      video: isVideo,
      carousel: !!nextBtn || slides > 1 || imgIdx,
      vis: vis,
      dataVis: dataVis,
    });
  }
  return out;
}
"""


def _find_count(text: str, rx) -> tuple:
    m = rx.search(text or "")
    if not m:
        return None, ""
    disp = m.group(1).strip()
    return parse_count(disp), disp


def _find_likes(text: str) -> tuple:
    """Curtidas em qualquer formato do feed: 'N curtidas' OU 'e outras N pessoas'."""
    n, disp = _find_count(text, _LIKES_RE)
    if n is not None:
        return n, disp
    return _find_count(text, _LIKES_RE2)


_NUM_LINE_RE = re.compile(r"^[\d.,]+(?:\s*(?:mil|mi|k|m))?$", re.I)


def _counts_from_lines(text: str) -> tuple:
    """Layout NOVO do feed: os numeros aparecem soltos, em sequencia, na barra de
    acoes — ex.: 'Seguir | 6,6 mil | 436 | 185' (curtidas, comentarios, compart.).
    Pega a 1a sequencia de 2+ linhas puramente numericas: 1a=curtidas, 2a=coments."""
    run = []
    for line in (text or "").splitlines():
        l = line.strip().replace("\xa0", " ")
        if l and _NUM_LINE_RE.match(l):
            run.append((parse_count(l), l))
            if len(run) == 3:
                break
        elif run:
            if len(run) >= 2:
                break
            run = []          # numero isolado (ex.: '1' de '1 d' nao chega aqui)
    if len(run) >= 2:
        return run[0][0], run[0][1], run[1][0], run[1][1]
    return None, "", None, ""


def _extract_counts(text: str) -> tuple:
    """(likes_n, likes_disp, comm_n, comm_disp) tentando todos os formatos:
    com palavras ('N curtidas'/'outras N pessoas') e o layout de numeros soltos."""
    likes_n, likes_disp = _find_likes(text)
    comm_n, comm_disp = _find_count(text, _COMM_RE)
    if likes_n is None or comm_n is None:
        l2, ld2, c2, cd2 = _counts_from_lines(text)
        if likes_n is None and l2 is not None:
            likes_n, likes_disp = l2, ld2
        if comm_n is None and c2 is not None:
            comm_n, comm_disp = c2, cd2
    return likes_n, likes_disp, comm_n, comm_disp


def _passes(cfg: dict, art: dict, likes_n, comm_n) -> tuple:
    """(aprovada?, motivo da recusa)."""
    if art.get("video"):
        return False, "vídeo/reel"
    if cfg.get("only_carousels", True) and not art.get("carousel"):
        return False, "não é carrossel"
    if likes_n is None:
        return False, "curtidas ocultas/não lidas"
    if likes_n < cfg.get("likes_min", 0):
        return False, "curtidas abaixo do mínimo"
    if likes_n > cfg.get("likes_max", 10**9):
        return False, "curtidas acima do teto"
    # Regra "E": precisa passar em curtidas E em comentarios (pedido do usuario)
    cmin = cfg.get("comments_min", 0)
    if cmin:
        if comm_n is None:
            return False, "comentários não lidos"
        if comm_n < cmin:
            return False, "comentários abaixo do mínimo"
    return True, ""


def _caption_from_text(text: str) -> str:
    """Heuristica: a linha de texto mais longa do card (fora dos contadores)."""
    lines = [l.strip() for l in (text or "").splitlines() if len(l.strip()) > 20]
    lines = [l for l in lines if not _LIKES_RE.search(l) and not _COMM_RE.search(l)]
    return max(lines, key=len)[:400] if lines else ""


def _download_thumb(sess: requests.Session, url: str, feed_id: str) -> str:
    if not url:
        return ""
    try:
        r = sess.get(url, timeout=20, headers={"User-Agent": _UA})
        r.raise_for_status()
        p = feedinbox.feed_thumb_dir(feed_id) / f"{uuid.uuid4().hex}.jpg"
        p.write_bytes(r.content)
        return str(p)
    except Exception:
        return ""


def collect(feed_id: str = None, minutes: int = None, progress_cb=None,
            login_wait_cb=None, should_stop=None) -> int:
    """Rola o feed da conta-isca e adiciona ao inbox o que passar no filtro.
    Retorna quantas publicacoes novas entraram. should_stop: threading.Event."""
    feed = feedinbox.get_feed(feed_id) if feed_id else feedinbox.get_or_create_default_feed()
    if not feed:
        return 0
    feed_id = feed["id"]
    cfg = {**feedinbox.DEFAULT_CONFIG, **(feed.get("config") or {})}
    minutes = minutes or cfg.get("scroll_minutes", 10)
    known = feedinbox.known_shortcodes(feed_id)
    found = 0

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stealth = Stealth()
    _report(progress_cb,
            f"Feed '{feed.get('name', '?')}': coletando por {minutes} min "
            f"(likes {cfg['likes_min']:,}–{cfg['likes_max']:,} E comentários ≥ "
            f"{cfg.get('comments_min', 0)}) — início às "
            f"{datetime.now().strftime('%H:%M:%S')}".replace(",", "."))
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            args=[
                "--disable-blink-features=AutomationControlled",
                # Janelas por cima NAO pausam o render/lazy-load do feed — a
                # coleta segue mesmo com o navegador coberto (melhor que pausar)
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
        )
        stealth.apply_stealth_sync(context)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            if not _wait_instagram_login(context, page, progress_cb, login_wait_cb):
                _report(progress_cb, "Sem login na conta-isca — coleta cancelada.")
                return 0
            if "instagram.com" not in page.url or "login" in page.url:
                page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

            # 🛡 ESCUDO: a janela do robo passa a IGNORAR mouse/teclado do usuario
            # (rolagem/cliques manuais nao atrapalham a coleta). Se a roda do bot
            # tambem for bloqueada pelo escudo, ha troca automatica p/ rolagem JS.
            try:
                cdp = context.new_cdp_session(page)
                cdp.send("Input.setIgnoreInputEvents", {"ignore": True})
                _report(progress_cb, "🛡 Janela blindada: mouse/teclado manuais não afetam a coleta.")
            except Exception:
                _report(progress_cb, "Não foi possível blindar a janela — seguindo sem o escudo.")

            sess = requests.Session()
            deadline = time.monotonic() + minutes * 60
            js_scroll = False
            last_y = None
            stuck = 0
            seen = 0
            rejects = {}          # motivo -> quantas (resumo de diagnostico no fim)
            diag_snippets = 0     # amostras de texto quando as curtidas nao sao lidas
            empty_cycles = 0
            last_beat = time.monotonic()
            while time.monotonic() < deadline:
                if should_stop is not None and should_stop.is_set():
                    _report(progress_cb, "Coleta interrompida pelo usuário.")
                    break
                try:
                    arts = page.evaluate(_EXTRACT_JS)
                except Exception:
                    arts = []
                if not arts:
                    empty_cycles += 1
                    if empty_cycles == 8:
                        _report(progress_cb,
                                "⚠ Nenhuma publicação detectada há vários ciclos — o layout "
                                "do Instagram pode ter mudado. Me mostre este LOG.")
                else:
                    empty_cycles = 0
                on_taste = False
                for art in arts:
                    sc = art.get("sc", "")
                    if not sc or sc in known:
                        continue
                    # Estrategia A: so avalia com >=60% do post na tela (conteudo
                    # montado). Estrategia B (resgate): post subindo com o topo
                    # cortado mas com o rodape de dados visivel tambem vale — os
                    # contadores ja montaram quando ele passou pelo centro.
                    if float(art.get("vis") or 0) < 0.6 and not art.get("dataVis"):
                        continue
                    known.add(sc)
                    seen += 1
                    text = art.get("text", "")
                    likes_n, likes_disp, comm_n, comm_disp = _extract_counts(text)
                    ok, reason = _passes(cfg, art, likes_n, comm_n)
                    label = f"{sc} (curtidas {likes_disp or '?'} · comentários {comm_disp or '?'})"
                    if not ok:
                        rejects[reason] = rejects.get(reason, 0) + 1
                        _report(progress_cb, f"  ✗ {label} — {reason}")
                        if reason == "curtidas ocultas/não lidas" and diag_snippets < 3:
                            diag_snippets += 1
                            snippet = " | ".join((text or "").split("\n"))[:170]
                            _report(progress_cb, f"     [diagnóstico] texto do card: {snippet}")
                        continue
                    thumb = _download_thumb(sess, art.get("img", ""), feed_id)
                    feedinbox.add_item(
                        feed_id, sc, likes_disp, comm_disp, likes_n, comm_n,
                        _caption_from_text(text), thumb, art.get("carousel", False),
                    )
                    found += 1
                    on_taste = True
                    _report(progress_cb, f"  ✔ {label} — entrou no feed!")
                if time.monotonic() - last_beat > 60:
                    last_beat = time.monotonic()
                    _report(progress_cb, f"— andamento: {seen} vistas · {found} aprovadas —")
                # Jardineiro do algoritmo: demora nas boas, passa rapido nas ruins
                page.wait_for_timeout(int(random.uniform(2500, 5000) if on_taste
                                          else random.uniform(600, 1400)))
                # Rolagem: roda do mouse por padrao; se o escudo tambem travar a
                # roda do bot (scrollY parado 3 ciclos), troca p/ rolagem via JS
                if not js_scroll:
                    try:
                        y = page.evaluate("window.scrollY")
                    except Exception:
                        y = None
                    if y is not None:
                        if last_y is not None and abs(y - last_y) < 5:
                            stuck += 1
                            if stuck >= 3:
                                js_scroll = True
                                _report(progress_cb,
                                        "Roda do mouse não avançou — trocando para rolagem via página (JS).")
                        else:
                            stuck = 0
                        last_y = y
                if js_scroll:
                    try:
                        page.evaluate(f"window.scrollBy(0, {random.randint(500, 900)})")
                    except Exception:
                        pass
                else:
                    page.mouse.wheel(0, random.randint(500, 900))
            if rejects:
                parts = " · ".join(f"{k}: {v}" for k, v in
                                   sorted(rejects.items(), key=lambda kv: -kv[1]))
                _report(progress_cb, f"Resumo: {seen} vistas · {found} aprovadas · recusas → {parts}")
            else:
                _report(progress_cb, f"Resumo: {seen} vistas · {found} aprovadas")
        finally:
            try:
                context.close()
            except Exception:
                pass

    feedinbox.set_last_collect(feed_id, datetime.now().strftime("%d/%m/%Y %H:%M"))
    _report(progress_cb, f"Coleta concluída: {found} publicação(ões) nova(s) no feed.")
    return found


if __name__ == "__main__":
    # CLI para rodar o coletor avulso (e, na Fase 3, dentro de uma VM/cloud)
    import argparse
    ap = argparse.ArgumentParser(description="Coletor do Feed Especial (conta-isca)")
    ap.add_argument("--minutes", type=int, default=None, help="duração da coleta")
    args = ap.parse_args()
    collect(minutes=args.minutes, progress_cb=print)
