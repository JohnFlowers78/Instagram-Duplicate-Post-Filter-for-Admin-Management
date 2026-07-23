"""Postagem/Programação no Instagram via uiautomator2 (Android emulador/celular).

Substitui o poster.py (navegador) para as estratégias "Emulador" e "Celular".
TODOS os seletores vêm do POSTFLOW_INSTAGRAM.md (mapeado ao vivo no aparelho).

Filosofia:
- Cada aparelho é acessado pelo seu SERIAL (adb), então emulador e celular físico
  convivem sem ambiguidade (ao contrário do adb "solto" com 2 aparelhos).
- Navegação e checagem de conta são SEGURAS (não publicam). A publicação de fato
  só roda em post_carousel() e só quando chamada explicitamente.
- Degrada com elegância: sem uiautomator2 instalado, ok=False e mensagem clara.

Ordem do fluxo (POSTFLOW): abrir app → perfil → conferir/trocar conta →
Criar post → selecionar imagens (ordem por data) → Taxa=Retrato → (música manual)
→ Avançar → legenda → colaboradores → Mais opções → Programar (roda ou relógio)
→ Compartilhar/Programar.
"""

import time

try:
    import uiautomator2 as u2
    _HAS_U2 = True
except Exception:            # pragma: no cover - ambiente sem a lib
    u2 = None
    _HAS_U2 = False

PKG = "com.instagram.android"


def _rid(name: str) -> str:
    return f"{PKG}:id/{name}"


class IGDriver:
    """Uma sessão de automação ligada a UM aparelho (serial)."""

    def __init__(self, serial: str = "emulator-5554", report=None, timeout: float = 15.0):
        self.serial = serial
        self.timeout = timeout
        self._report = report or (lambda m: None)
        self.d = None

    # ---- infra -------------------------------------------------------------
    def log(self, msg: str):
        try:
            self._report(msg)
        except Exception:
            pass

    def connect(self):
        if not _HAS_U2:
            raise RuntimeError("uiautomator2 não instalado (pip install uiautomator2)")
        self.d = u2.connect(self.serial)
        return self.d

    def _el(self, **kw):
        return self.d(**kw)

    def _wait_click(self, label: str, timeout=None, **kw) -> bool:
        """Espera um elemento aparecer e clica. Retorna True/False (não levanta)."""
        el = self.d(**kw)
        if el.wait(timeout=timeout or self.timeout):
            el.click()
            self.log(f"• toquei em {label}")
            return True
        self.log(f"⚠ não achei {label} ({kw})")
        return False

    # ---- app / navegação ---------------------------------------------------
    def open_app(self, fresh: bool = True):
        """Abre o Instagram. fresh=True FECHA antes (garante abrir no Feed, não
        retomar uma tela anterior como o compositor/agendador)."""
        if fresh:
            self.d.app_stop(PKG)
            time.sleep(0.8)
        self.d.app_start(PKG, use_monkey=True)
        self.log("• Instagram aberto (Feed)")
        time.sleep(2.5)

    def go_to_profile(self) -> bool:
        """Feed → Perfil (barra inferior)."""
        ok = self._wait_click("aba Perfil", resourceId=_rid("profile_tab"))
        if ok:
            self.d(resourceId=_rid("action_bar_title")).wait(timeout=self.timeout)
        return ok

    def go_to_feed(self) -> bool:
        return self._wait_click("aba Feed", resourceId=_rid("feed_tab"))

    # ---- conta -------------------------------------------------------------
    def active_account(self) -> str:
        """@ da conta ativa (lido no topo do perfil). '' se não estiver no perfil."""
        el = self.d(resourceId=_rid("action_bar_title"))
        if el.exists:
            try:
                return (el.get_text() or "").strip()
            except Exception:
                return ""
        return ""

    def switch_account(self, target: str, confirm: bool = True) -> bool:
        """Troca para a conta @target via clique-longo na foto de Perfil.
        Casa pelo content-desc da linha (== @target ou começa com @target)."""
        target = target.lstrip("@").strip()
        cur = self.active_account()
        if cur.lstrip("@") == target:
            self.log(f"• já estou em @{target}")
            return True
        prof = self.d(resourceId=_rid("profile_tab"))
        if not prof.wait(timeout=self.timeout):
            self.log("⚠ aba Perfil ausente para o clique-longo")
            return False
        prof.long_click()
        self.log("• clique-longo na foto de Perfil (abriu seletor de contas)")
        time.sleep(1.2)
        # linha exata, senão linha que começa com o @ (tem sufixo de notificações)
        row = self.d(description=target)
        if not row.exists:
            row = self.d(descriptionStartsWith=target)
        if not row.wait(timeout=self.timeout):
            self.log(f"⚠ conta @{target} não está logada neste aparelho")
            self.d.press("back")
            return False
        row.click()
        self.log(f"• toquei na conta @{target}")
        time.sleep(2.5)   # a troca cai no FEED da nova conta (não no perfil)
        if confirm:
            self.go_to_profile()   # volta ao perfil p/ ler o @ ativo
            now = self.active_account().lstrip("@")
            if now == target:
                self.log(f"✓ conta trocada para @{target}")
                return True
            self.log(f"⚠ troca não confirmada (ativa: @{now})")
            return False
        return True

    def ensure_account(self, target: str) -> bool:
        """Garante @target ativa: vai ao perfil, confere e troca se preciso."""
        self.go_to_profile()
        if self.active_account().lstrip("@") == target.lstrip("@").strip():
            self.log(f"✓ conta correta (@{target.lstrip('@')})")
            return True
        return self.switch_account(target)

    # ---- criação (só ABRE o menu; não publica) -----------------------------
    def open_create_post(self) -> bool:
        """Perfil → Criar novo → Criar novo post (chega na seleção de imagens)."""
        if not self._wait_click("Criar novo", description="Criar novo"):
            return False
        time.sleep(0.8)
        return self._wait_click("Criar novo post", description="Criar novo post")


# --- rotina de VALIDAÇÃO (assistível, NÃO publica) -------------------------
def navtest(serial: str = "emulator-5554", target_account: str = "",
            open_create: bool = False, report=None) -> dict:
    """Abre o app, vai ao perfil, mostra a conta ativa, (opcional) troca de conta
    e (opcional) abre o compositor de Post. NÃO publica nada — é o teste que o
    usuário assiste para validar todo o mapa de navegação."""
    r = {"ok": False, "account": "", "error": ""}
    drv = IGDriver(serial, report=report)
    try:
        drv.connect()
        drv.open_app(fresh=True)
        drv.go_to_profile()
        r["account"] = drv.active_account()
        drv.log(f"→ conta ativa: @{r['account'] or '???'}")
        if target_account and target_account.lstrip("@") != r["account"].lstrip("@"):
            drv.switch_account(target_account)
            r["account"] = drv.active_account()
        if open_create:
            if drv.open_create_post():
                drv.log("→ compositor de Post aberto (parando aqui; nada publicado)")
            else:
                drv.log("⚠ não consegui abrir o compositor")
        r["ok"] = True
    except Exception as exc:
        r["error"] = str(exc)
        drv.log(f"ERRO: {exc}")
    return r


if __name__ == "__main__":
    import argparse, sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Teste de navegação do IG (não publica).")
    ap.add_argument("serial", nargs="?", default="emulator-5554")
    ap.add_argument("--conta", default="", help="@ da conta de destino (troca se preciso)")
    ap.add_argument("--criar", action="store_true", help="abrir o compositor de Post ao final")
    a = ap.parse_args()
    out = navtest(a.serial, a.conta, a.criar, report=print)
    print("\nRESULTADO:", out)
