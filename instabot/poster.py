"""Postagem no Instagram por navegador (a 'mão' do agendador).

⚠⚠ ESQUELETO — os PASSOS do modal de criação do Instagram (selecionar arquivos →
recorte → próximo → legenda → marcar pessoas → MÚSICA em alta → compartilhar)
estão marcados com TODO e AINDA NÃO clicam de verdade. O usuário vai enviar os
prints/passo-a-passo dessa tela; só então os seletores entram (mesmo método
best-effort do feedbot/chatgpt). Ver ESTRATEGIAS.md.

O que JÁ está pronto: perfil próprio (conta de postagem, separada por segurança),
login guard, ordem das imagens (numérica), leitura da Legenda.txt, contas @ a marcar.
NÃO postar nada real enquanto os TODOs não forem preenchidos e testados.
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

import dedup
from paths import DATA_DIR

PROFILE_DIR = DATA_DIR / "poster_profile"   # conta EXCLUSIVA de postagem (segurança)
INSTAGRAM_URL = "https://www.instagram.com/"

IMPLEMENTED = False   # vira True quando os TODOs do modal estiverem prontos e testados


def _report(cb, msg):
    if cb:
        try:
            cb(msg)
        except Exception:
            pass


def slot_images(slot: Path) -> list:
    """Imagens do carrossel na ORDEM correta (1,2,3...)."""
    return dedup._sorted_numbered_images(slot)


def slot_caption(slot: Path) -> str:
    """Legenda do post = conteúdo de Legenda.txt."""
    for name in ("Legenda.txt", "legenda.txt"):
        p = slot / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    return ""


def _pick_trending_music_js():
    """Seletor (a preencher com os prints): itens de música com a flecha ↗
    'em alta'. Retorna os índices/handles clicáveis. TODO."""
    # Ex. futuro: procurar no painel de músicas os itens que contêm o ícone de
    # tendência (svg/aria-label específico) e devolver um deles ao acaso.
    return []


def post_carousel(slot: Path, caption: str, tagged: list,
                  progress_cb=None, login_wait_cb=None) -> dict:
    """Publica UM carrossel. Retorna {'ok': bool, 'error': str}.
    Enquanto IMPLEMENTED=False, apenas valida e simula (não publica)."""
    result = {"ok": False, "error": ""}
    imgs = slot_images(Path(slot))
    if not imgs:
        result["error"] = "sem imagens no slot"
        return result
    _report(progress_cb, f"Preparando {Path(slot).name}: {len(imgs)} imagem(ns), "
                         f"{len(caption)} car. de legenda, {len(tagged)} marcação(ões)")

    if not IMPLEMENTED:
        _report(progress_cb, "⚠ Publicação real desativada (aguardando os prints do "
                             "modal do Instagram). Simulação concluída — nada foi postado.")
        result["error"] = "not_implemented"
        return result

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stealth = Stealth()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            args=["--disable-blink-features=AutomationControlled",
                  "--disable-backgrounding-occluded-windows",
                  "--disable-renderer-backgrounding"],
        )
        stealth.apply_stealth_sync(context)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(INSTAGRAM_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            # from downloader import _wait_instagram_login
            # if not _wait_instagram_login(context, page, progress_cb, login_wait_cb): ...

            # TODO(prints): 1) clicar em "Criar" (＋) / "Nova publicação"
            # TODO(prints): 2) set_input_files(imgs)  — envia todas na ordem
            # TODO(prints): 3) recorte → "Avançar"; efeitos → "Avançar"
            # TODO(prints): 4) escrever a legenda (caption)
            # TODO(prints): 5) marcar pessoas (tagged) — abrir, digitar @, confirmar
            # TODO(prints): 6) MÚSICA: abrir painel, filtrar as com flecha ↗ (em alta),
            #                escolher UMA ao acaso  (_pick_trending_music_js)
            # TODO(prints): 7) "Compartilhar" e aguardar confirmação de publicado
            result["ok"] = True
        except Exception as exc:
            result["error"] = str(exc)
            _report(progress_cb, f"ERRO: {exc}")
        finally:
            try:
                context.close()
            except Exception:
                pass
    return result
