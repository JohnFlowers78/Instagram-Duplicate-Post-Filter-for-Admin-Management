"""Automacao best-effort do chatgpt.com (sem API paga) para o modulo
'Edicao CARDs Finais'. Perfil de Chrome PROPRIO (conta-isca do usuario no
ChatGPT), no mesmo padrao do Instagram/Feed.

⚠ FRAGIL: o DOM do chatgpt.com muda com frequencia. As estrategias de seletor
estao em camadas e todas logam no progress_cb — quando algo quebrar, o LOG diz
onde. Refinar com feedback real (mesmo metodo do feedbot). Ver ESTRATEGIAS.md.
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from paths import DATA_DIR

PROFILE_DIR = DATA_DIR / "chatgpt_profile"
CHATGPT_URL = "https://chatgpt.com/"


def _report(cb, msg):
    if cb:
        try:
            cb(msg)
        except Exception:
            pass


def logged_in(page) -> bool:
    """Heuristica: logado se existe a caixa de composicao (textarea/#prompt)."""
    try:
        return bool(page.query_selector("#prompt-textarea") or
                    page.query_selector('textarea[data-testid], div[contenteditable="true"]'))
    except Exception:
        return False


def _wait_login(page, progress_cb=None, login_wait_cb=None, timeout_s=300) -> bool:
    if logged_in(page):
        return True
    _report(progress_cb, "ChatGPT SEM LOGIN — faça login na janela do Chrome…")
    if login_wait_cb:
        try:
            login_wait_cb(True)
        except Exception:
            pass
    ok = False
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        page.wait_for_timeout(3000)
        if logged_in(page):
            ok = True
            break
    if login_wait_cb:
        try:
            login_wait_cb(False)
        except Exception:
            pass
    _report(progress_cb, "Login detectado! Continuando…" if ok
            else "Sem login após aguardar — cancelado.")
    return ok


def _find_composer(page):
    for sel in ("#prompt-textarea",
                'div[contenteditable="true"]',
                'textarea[data-testid]',
                "textarea"):
        el = page.query_selector(sel)
        if el:
            return el, sel
    return None, ""


def send_prompt(prompt: str, image_paths: list, progress_cb=None,
                login_wait_cb=None, headless: bool = False) -> dict:
    """Abre o ChatGPT, anexa as imagens (ate 30), envia o prompt e devolve
    {'text': resposta, 'images': [caminhos das imagens geradas baixadas]}.

    Best-effort: em caso de erro, retorna o que conseguiu e loga o passo."""
    result = {"text": "", "images": [], "error": ""}
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stealth = Stealth()
    _report(progress_cb, "Abrindo o ChatGPT…")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=headless,
            viewport={"width": 1200, "height": 860},
            locale="pt-BR",
            args=["--disable-blink-features=AutomationControlled"],
        )
        stealth.apply_stealth_sync(context)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(CHATGPT_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            if not _wait_login(page, progress_cb, login_wait_cb):
                result["error"] = "sem login"
                return result

            # 1) Anexa as imagens (ate 30) — via input[type=file] escondido
            imgs = [str(p_) for p_ in image_paths if Path(p_).is_file()][:30]
            if imgs:
                _report(progress_cb, f"Anexando {len(imgs)} imagem(ns)…")
                try:
                    finput = page.query_selector('input[type="file"]')
                    if finput:
                        finput.set_input_files(imgs)
                        page.wait_for_timeout(1500 + 400 * len(imgs))
                    else:
                        _report(progress_cb, "⚠ Não achei o campo de anexo — enviando só o texto.")
                except Exception as exc:
                    _report(progress_cb, f"⚠ Falha ao anexar: {exc}")

            # 2) Escreve o prompt e envia
            comp, sel = _find_composer(page)
            if not comp:
                result["error"] = "caixa de mensagem não encontrada (layout mudou?)"
                _report(progress_cb, "⚠ " + result["error"])
                return result
            _report(progress_cb, f"Escrevendo o script (caixa: {sel})…")
            comp.click()
            page.keyboard.insert_text(prompt)
            page.wait_for_timeout(600)
            page.keyboard.press("Enter")
            _report(progress_cb, "Prompt enviado — aguardando a resposta…")

            # 3) Espera a geracao terminar (some o botao 'parar'/stop)
            deadline = time.monotonic() + 240
            page.wait_for_timeout(4000)
            while time.monotonic() < deadline:
                stop = page.query_selector('button[data-testid="stop-button"], '
                                           'button[aria-label*="Parar"], '
                                           'button[aria-label*="Stop"]')
                if not stop:
                    break
                page.wait_for_timeout(1500)
            page.wait_for_timeout(1500)

            # 4) Le o texto da ultima resposta do assistente
            try:
                blocks = page.query_selector_all('[data-message-author-role="assistant"]')
                if blocks:
                    result["text"] = (blocks[-1].inner_text() or "").strip()
            except Exception:
                pass

            # 5) Baixa imagens geradas na ultima resposta (best-effort)
            try:
                import requests
                out_dir = None
                from cardscripts import gen_dir
                out_dir = gen_dir()
                srcs = page.evaluate(
                    """() => {
                        const blocks = document.querySelectorAll('[data-message-author-role="assistant"]');
                        if (!blocks.length) return [];
                        const last = blocks[blocks.length - 1];
                        return [...last.querySelectorAll('img')]
                            .map(i => i.currentSrc || i.src)
                            .filter(s => s && s.startsWith('http'));
                    }"""
                ) or []
                stamp = time.strftime("%Y-%m-%d_%H%M%S")
                for i, s in enumerate(srcs, 1):
                    try:
                        r = requests.get(s, timeout=30)
                        r.raise_for_status()
                        fp = out_dir / f"card_{stamp}_{i}.png"
                        fp.write_bytes(r.content)
                        result["images"].append(str(fp))
                    except Exception:
                        pass
                if result["images"]:
                    _report(progress_cb, f"{len(result['images'])} imagem(ns) baixada(s).")
            except Exception:
                pass

            _report(progress_cb, "Concluído.")
        except Exception as exc:
            result["error"] = str(exc)
            _report(progress_cb, f"ERRO: {exc}")
        finally:
            try:
                context.close()
            except Exception:
                pass
    return result
