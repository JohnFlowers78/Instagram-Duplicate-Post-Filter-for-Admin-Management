from pathlib import Path
from typing import Callable, Optional

import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from paths import DATA_DIR

SNAPINSTA_URL = "https://snapinsta.to/pt"
PROFILE_DIR = DATA_DIR / "browser_profile"

ProgressCallback = Optional[Callable[[str], None]]

_DOWNLOAD_HEADERS = {
    "Referer": "https://snapinsta.to/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0 Safari/537.36"
    ),
}

# Textos que indicam erro de "publicacao privada" no snapinsta.to
_PRIVATE_PHRASES = [
    "link privado",
    "publicação privada",
    "publicacao privada",
    "private link",
    "private post",
    "perfil privado",
    "private profile",
]

# Seletores para botoes de fechar popup/modal (em ordem de preferencia)
_CLOSE_SELECTORS = [
    "#closeModalBtn",
    "button:has-text('Fechar')",
    "a:has-text('Fechar')",
    "button:has-text('fechar')",
    "button:has-text('Close')",
    "[class*='btn-close']:visible",
    "[class*='close-btn']:visible",
    "[class*='modal'] button:visible",
]


class DownloadError(Exception):
    pass


def _report(cb: ProgressCallback, msg: str) -> None:
    if cb:
        cb(msg)


def _close_popups(page) -> bool:
    """Tenta fechar qualquer popup/modal visivel. Retorna True se fechou algum."""
    closed = False
    for sel in _CLOSE_SELECTORS:
        try:
            loc = page.locator(sel)
            for i in range(loc.count()):
                el = loc.nth(i)
                if el.is_visible(timeout=300):
                    el.click(timeout=1500)
                    closed = True
                    page.wait_for_timeout(300)
        except Exception:
            pass
    return closed


def _check_private_error(page) -> bool:
    """Retorna True se o snapinsta.to exibir mensagem de link/perfil privado."""
    try:
        body = page.locator("body").inner_text(timeout=3000).lower()
        return any(phrase in body for phrase in _PRIVATE_PHRASES)
    except Exception:
        return False


def _extract_links(page) -> list[str]:
    """Extrai todos os links de download direto dos cards .download-items."""
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('.download-items')).map(el => {
            const a = el.querySelector('a.download-items__btn, a[href*="snapcdn.app"]');
            return a ? a.href : null;
        }).filter(Boolean)
    """)


def _extract_ig_meta(page) -> dict:
    """Extrai curtidas e comentarios do DOM do Instagram (requer sessao autenticada).

    Estrategia: os SVG[aria-label="Curtir"] de reacoes de comentarios aparecem ANTES
    da barra de acoes no DOM — usa o ULTIMO SVG Curtir da pagina (sempre o da barra
    de acoes). Comentar aparece apenas uma vez (barra de acoes), entao querySelector basta.
    """
    meta = {"likes": "N/D", "comments": "N/D", "views": "N/D"}
    try:
        result = page.evaluate("""
            () => {
                const out = {likes: null, comments: null};

                const allCurtirSvgs = [...document.querySelectorAll('svg[aria-label="Curtir"]')];
                const curtirSvg     = allCurtirSvgs[allCurtirSvgs.length - 1] || null;
                const comentarSvg   = document.querySelector('svg[aria-label="Comentar"]');

                // Estrategia 1: container comum do ultimo Curtir + Comentar (barra de acoes).
                // findCountFromSvg procura o proximo [role=button] numerico logo apos o
                // botao-icone, parando ao encontrar o proximo botao com SVG.
                if (curtirSvg && comentarSvg) {
                    let container = comentarSvg.parentElement;
                    for (let d = 0; d < 10; d++) {
                        if (!container || container === document.body) { container = null; break; }
                        if (container.contains(curtirSvg)) break;
                        container = container.parentElement;
                    }

                    if (container) {
                        const allBtns = [...container.querySelectorAll('[role="button"]')];

                        const findCountFromSvg = (svg) => {
                            const btn = svg && svg.closest('[role="button"]');
                            if (!btn) return null;
                            const start = allBtns.indexOf(btn);
                            if (start < 0) return null;
                            for (let i = start + 1; i < allBtns.length; i++) {
                                const el = allBtns[i];
                                if (el.querySelector('svg')) break;
                                const t = (el.textContent || '').replace(/\\u00a0/g, ' ').trim();
                                if (/^[\\d.,]+(?:\\s*[a-z]{1,3})?$/i.test(t) && t.length < 20)
                                    return t;
                            }
                            return null;
                        };

                        out.likes    = findCountFromSvg(curtirSvg);
                        out.comments = findCountFromSvg(comentarSvg);
                    }
                }

                // Estrategia 2 (fallback): traversia pai → proximo irmao [role=button] numerado.
                if (!out.likes || !out.comments) {
                    const svgForField = { likes: curtirSvg, comments: comentarSvg };
                    for (const [field, svg] of Object.entries(svgForField)) {
                        if (out[field] || !svg) continue;
                        const btn = svg.closest('[role="button"]');
                        if (!btn) continue;
                        let node = btn;
                        for (let depth = 0; depth < 7; depth++) {
                            node = node.parentElement;
                            if (!node) break;
                            const sib = node.nextElementSibling;
                            if (sib && sib.getAttribute('role') === 'button') {
                                const t = (sib.textContent || '').replace(/\\u00a0/g, ' ').trim();
                                if (/^\\d/.test(t) && t.length < 20) { out[field] = t; break; }
                            }
                        }
                    }
                }

                // Estrategia 3 (ultimo recurso): "N curtidas" como texto completo.
                // Usa o ULTIMO match — comentarios vem antes da barra de acoes no DOM.
                if (!out.likes) {
                    let lastMatch = null;
                    for (const el of document.querySelectorAll('[role="button"]')) {
                        const t = (el.textContent || '').replace(/\\u00a0/g, ' ').trim();
                        const m = t.match(/^([\\d.,]+(?:\\s*mi(?:l)?)?)\\s+curtida[s]?$/i);
                        if (m && m[1]) lastMatch = m[1].trim();
                    }
                    if (lastMatch) out.likes = lastMatch;
                }

                return { likes: out.likes || 'N/D', comments: out.comments || 'N/D' };
            }
        """)
        if result:
            for k, v in result.items():
                if v and v != "N/D":
                    meta[k] = v
    except Exception:
        pass
    return meta


def download_carousel(
    instagram_url: str,
    dest_folder: Path,
    progress_cb: ProgressCallback = None,
) -> tuple[list[Path], dict]:
    dest_folder.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stealth = Stealth()
    ig_meta: dict = {"likes": "N/D", "comments": "N/D", "views": "N/D"}

    _report(progress_cb, "Abrindo navegador...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            args=["--disable-blink-features=AutomationControlled"],
        )
        stealth.apply_stealth_sync(context)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            _report(progress_cb, "Carregando snapinsta.to...")
            page.goto(SNAPINSTA_URL, wait_until="load", timeout=60000)

            # Aguarda a pagina estabilizar e fecha qualquer popup inicial
            page.wait_for_timeout(2500)
            _close_popups(page)
            page.wait_for_timeout(500)
            _close_popups(page)  # segunda tentativa caso haja mais de um modal

            _report(progress_cb, "Colando o link da publicacao...")
            page.fill("#s_input", instagram_url)
            page.wait_for_timeout(300)

            _report(progress_cb, "Solicitando processamento...")
            page.click("button[onclick*='ksearchvideo']")

            # --- Aguarda resultados, fechando propagandas conforme aparecem ---
            _report(progress_cb, "Aguardando resultados (pode aparecer propaganda para fechar)...")
            links: list[str] = []
            for attempt in range(25):
                page.wait_for_timeout(2000)

                # Fecha qualquer modal/popup que aparecer (incluindo OpportunItaly)
                _close_popups(page)

                # Verifica erro de publicacao privada
                if _check_private_error(page):
                    raise DownloadError(
                        "O snapinsta.to indicou que esta publicacao e privada.\n"
                        "Isso e um bug temporario do site — aguarde alguns minutos e tente novamente."
                    )

                links = _extract_links(page)
                if links:
                    break

            if not links:
                raise DownloadError(
                    "O snapinsta.to nao retornou midias para esse link apos aguardar.\n"
                    "Verifique se o link do Instagram esta correto e tente novamente."
                )

            # Visita o Instagram para capturar curtidas/comentarios enquanto o
            # navegador ainda esta aberto. Requer login no Instagram no navegador do bot.
            try:
                _report(progress_cb, "Coletando dados da publicacao no Instagram...")
                page.goto(instagram_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2500)
                ig_meta = _extract_ig_meta(page)
            except Exception:
                pass
        finally:
            context.close()

    _report(progress_cb, f"Baixando {len(links)} imagem(ns)...")
    saved: list[Path] = []
    with requests.Session() as session:
        for idx, url in enumerate(links, start=1):
            resp = session.get(url, headers=_DOWNLOAD_HEADERS, timeout=60)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "video" in content_type:
                ext = ".mp4"
            elif "png" in content_type:
                ext = ".png"
            else:
                ext = ".jpg"
            out_path = dest_folder / f"raw_{idx}{ext}"
            out_path.write_bytes(resp.content)
            saved.append(out_path)
            _report(progress_cb, f"  {idx}/{len(links)}: {out_path.name}")

    return saved, ig_meta
