from pathlib import Path
from typing import Callable, Optional

import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

SNAPINSTA_URL = "https://snapinsta.to/pt"
PROFILE_DIR = Path(__file__).parent / "data" / "browser_profile"

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


def download_carousel(
    instagram_url: str,
    dest_folder: Path,
    progress_cb: ProgressCallback = None,
) -> list[Path]:
    dest_folder.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stealth = Stealth()

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

    return saved
