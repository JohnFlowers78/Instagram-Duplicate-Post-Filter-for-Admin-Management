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

import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import uiautomator2 as u2
    _HAS_U2 = True
except Exception:            # pragma: no cover - ambiente sem a lib
    u2 = None
    _HAS_U2 = False

try:
    import androidenv
except Exception:            # pragma: no cover
    androidenv = None

PKG = "com.instagram.android"
CAROUSEL_REMOTE = "/sdcard/Pictures/postador"   # álbum dedicado do bot


def _bounds_center(b: str):
    """'[x1,y1][x2,y2]' → (cx, cy)."""
    m = re.findall(r"-?\d+", b)
    if len(m) < 4:
        return None
    x1, y1, x2, y2 = map(int, m[:4])
    return (x1 + x2) // 2, (y1 + y2) // 2


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

    # ---- seleção do carrossel NA ORDEM ------------------------------------
    def _adb(self, *args, timeout=60):
        adb = androidenv.adb_path() if androidenv else Path("adb")
        return subprocess.run([str(adb), "-s", self.serial, *args],
                              capture_output=True, text=True, timeout=timeout).stdout

    def push_carousel(self, local_paths, remote_dir: str = CAROUSEL_REMOTE) -> list:
        """Envia as imagens para um álbum DEDICADO, em ORDEM REVERSA e indexando
        UMA POR VEZ com intervalo: assim a imagem 1 é a ÚLTIMA indexada = a MAIS
        NOVA = primeira célula da grade. Depois basta tocar as células em ordem de
        leitura. (O 'criação em' do IG usa a data de indexação, não mtime/EXIF.)"""
        paths = [Path(p) for p in local_paths]
        self._adb("shell", "rm", "-rf", remote_dir)
        self._adb("shell", "mkdir", "-p", remote_dir)
        for p in reversed(paths):            # N, N-1, ..., 1  (1 fica por último)
            remote = f"{remote_dir}/{p.name}"
            self._adb("push", str(p), remote)
            self._adb("shell", "am", "broadcast", "-a",
                      "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote}")
            time.sleep(1.6)                  # date_added distinto (segundos)
        self.log(f"• {len(paths)} imagens enviadas ao álbum '{Path(remote_dir).name}' (ordem garantida)")
        return [f"{remote_dir}/{p.name}" for p in paths]

    def _photo_cells(self):
        """Células de FOTO da grade (com 'criação em' no desc), em ordem de leitura.
        Retorna lista de dicts {cx, cy, desc, selected}. As N primeiras = mais novas."""
        root = ET.fromstring(self.d.dump_hierarchy())
        cells, seen = [], set()
        for n in root.iter("node"):
            a = n.attrib
            rid = a.get("resource-id", "")
            desc = a.get("content-desc", "")
            if "gallery_grid_item_thumbnail" not in rid:
                continue
            if "cria" not in desc:           # ignora câmera/células sem foto
                continue
            b = a.get("bounds", "")
            if b in seen:
                continue
            seen.add(b)
            c = _bounds_center(b)
            if not c:
                continue
            cells.append({"cx": c[0], "cy": c[1], "desc": desc,
                          "selected": "selecionada" in desc})  # 'mídia selecionada N'
        return cells

    def enable_multiselect(self) -> bool:
        ms = self.d(resourceId=_rid("multi_select_slide_button_alt"))
        if ms.wait(timeout=self.timeout):
            ms.click()
            time.sleep(0.9)
            self.log("• múltipla seleção ativada")
            return True
        self.log("⚠ botão de múltipla seleção não encontrado")
        return False

    def select_carousel(self, n: int) -> bool:
        """Seleciona as n imagens (já enviadas por push_carousel) na ORDEM 1..n.
        Limpa qualquer seleção automática e toca as n primeiras células em leitura."""
        self.enable_multiselect()
        # 1) limpar seleção automática (a mais nova costuma vir marcada como '1')
        for _ in range(n + 2):
            sel = [c for c in self._photo_cells() if c["selected"]]
            if not sel:
                break
            self.d.click(sel[0]["cx"], sel[0]["cy"])
            time.sleep(0.5)
        # 2) tocar as n primeiras (mais novas) em ordem de leitura → carrossel 1..n
        cells = self._photo_cells()
        if len(cells) < n:
            self.log(f"⚠ só achei {len(cells)} fotos na grade (esperava {n})")
            return False
        for i in range(n):
            self.d.click(cells[i]["cx"], cells[i]["cy"])
            time.sleep(0.5)
        self.log(f"• {n} imagens tocadas na ordem (carrossel 1..{n})")
        return True

    # ---- BLOCO 2: edição (Taxa=Retrato) -----------------------------------
    def advance_selection(self) -> bool:
        """Grade de seleção → tela de edição (Avançar)."""
        return self._wait_click("Avançar (seleção)", resourceId=_rid("next_button_textview"))

    def set_aspect_portrait(self) -> bool:
        """Aba 'Taxa' → 'Retrato' → 'Concluir' (aplica proporção retrato a TODAS)."""
        if not self._wait_click("aba Taxa", text="Taxa"):
            return False
        time.sleep(0.8)
        if not self._wait_click("Retrato", text="Retrato"):
            # às vezes é 'Vertical'/'Retrato (4:5)'; tenta por prefixo
            self._wait_click("Retrato (prefixo)", textStartsWith="Retrato")
        time.sleep(0.5)
        return self._wait_click("Concluir (Taxa)", resourceId=_rid("bottom_sheet_done_button"))

    def advance_edit(self) -> bool:
        """Tela de edição → tela de legenda (Avançar)."""
        return self._wait_click("Avançar (edição)", resourceId=_rid("media_thumbnail_tray_button"))

    # ---- BLOCO 3: legenda + colaboradores ---------------------------------
    def set_caption(self, caption: str) -> bool:
        """Abre o editor dedicado de Legenda, escreve e confirma com 'OK' (volta
        à tela de compartilhar)."""
        el = self.d(resourceId=_rid("caption_input_text_view"))
        if not el.wait(timeout=self.timeout):
            self.log("⚠ campo de legenda não encontrado")
            return False
        el.click()               # abre a tela dedicada 'Legenda'
        time.sleep(0.6)
        field = self.d(resourceId=_rid("caption_input_text_view"))
        (field if field.exists else el).set_text(caption or "")
        self.log(f"• legenda escrita ({len(caption or '')} car.)")
        time.sleep(0.4)
        # confirmar: botão 'OK' (id=next_button_textview) → volta à tela de compartilhar
        ok = self.d(resourceId=_rid("next_button_textview"), description="OK")
        if not ok.exists:
            ok = self.d(resourceId=_rid("next_button_textview"))
        if ok.exists:
            ok.click()
            self.log("• legenda confirmada (OK)")
        else:
            self.d.press("back")
        time.sleep(1.2)
        return True

    def add_collaborators(self, users) -> bool:
        """Marcar pessoas → Convidar colaboradores → busca cada @ → Concluir."""
        users = [u.lstrip("@").strip() for u in (users or []) if u.strip()]
        if not users:
            return True
        if not self._wait_click("Marcar pessoas", resourceId=_rid("metadata_row_people")):
            return False
        time.sleep(0.8)
        if not self._wait_click("Convidar colaboradores", resourceId=_rid("invite_collaborator_button")):
            self.d.press("back")
            return False
        for user in users:
            se = self.d(resourceId=_rid("search_edit_text"))
            if not se.wait(timeout=self.timeout):
                self.log("⚠ busca de colaborador ausente")
                break
            se.set_text(user)
            time.sleep(1.5)
            # acha a linha cujo username == user
            hit = self.d(resourceId=_rid("row_search_user_username"), text=user)
            if not hit.wait(timeout=self.timeout):
                hit = self.d(resourceId=_rid("row_search_user_container"))
            if hit.exists:
                hit.click()
                self.log(f"• colaborador @{user} adicionado")
                time.sleep(1.0)
            else:
                self.log(f"⚠ colaborador @{user} não encontrado")
            try:
                se.set_text("")
            except Exception:
                pass
        # "V" (Concluir) = ImageView desc='Concluir'
        done = self.d(resourceId=_rid("action_bar_button_action"))
        ok = self._wait_click("Concluir (colaboradores)",
                              className="android.widget.ImageView", description="Concluir")
        return ok

    # ---- BLOCO 4: agendamento (Mais opções → Programar → data/hora) -------
    def _scroll_to(self, max_swipes=8, **kw) -> bool:
        for _ in range(max_swipes):
            if self.d(**kw).exists:
                return True
            self.d.swipe_ext("up", 0.6)
            time.sleep(0.5)
        return self.d(**kw).exists

    def open_more_options(self) -> bool:
        """Rola a tela de legenda até '... Mais opções' e abre."""
        if not self._scroll_to(textContains="Mais opções"):
            self.log("⚠ '...Mais opções' não encontrado")
            return False
        return self._wait_click("Mais opções", textContains="Mais opções")

    def toggle_schedule(self) -> bool:
        """Ativa a chave 'Programar esse post' (abre o overlay de data/hora)."""
        title = self.d(text="Programar esse post")
        if not title.wait(timeout=self.timeout):
            self.log("⚠ linha 'Programar esse post' ausente")
            return False
        # toca o ToggleButton da MESMA linha (sobe ao container e acha o toggle)
        try:
            self.d.xpath('//*[@text="Programar esse post"]/../..//*[@resource-id="%s"]'
                         % _rid("toggle")).click()
        except Exception:
            title.click()   # fallback: tocar a linha
        self.log("• chave 'Programar esse post' acionada")
        time.sleep(1.5)
        return True

    def detect_picker(self) -> str:
        """'roda' | 'relogio' | '' — qual overlay de data/hora apareceu."""
        if self.d(resourceId=_rid("numberpicker_input")).exists:
            return "roda"
        t = self.d(resourceId=_rid("title_text_view"))
        if (t.exists and (t.get_text() or "") == "Programar post") \
           or self.d(descriptionStartsWith="Data,").exists:
            return "relogio"
        return ""

    def set_datetime_relogio(self, dt) -> bool:
        """Estilo RELÓGIO: linha Data (calendário) + linha Horário (modo teclado)."""
        MES = ["janeiro","fevereiro","março","abril","maio","junho","julho",
               "agosto","setembro","outubro","novembro","dezembro"]
        # --- DATA ---
        if not self._wait_click("linha Data", descriptionStartsWith="Data,"):
            return False
        time.sleep(1.0)
        alvo_desc = f"{dt.day:02d} {MES[dt.month-1]} {dt.year}"
        for _ in range(14):   # avança meses se preciso
            day = self.d(description=alvo_desc)
            if day.exists:
                day.click()
                break
            nxt = self.d(resourceId="android:id/next")
            if not nxt.exists:
                nxt = self.d(description="Próximo mês")
            if nxt.exists:
                nxt.click(); time.sleep(0.6)
            else:
                break
        self._wait_click("OK (data)", resourceId="android:id/button1")
        time.sleep(0.8)
        # --- HORÁRIO (modo teclado) ---
        if not self._wait_click("linha Horário", descriptionStartsWith="Horário,"):
            return False
        time.sleep(1.0)
        tog = self.d(resourceId="android:id/toggle_mode")
        if tog.exists:
            tog.click(); time.sleep(0.6)
        h = self.d(resourceId="android:id/input_hour")
        m = self.d(resourceId="android:id/input_minute")
        if h.exists and m.exists:
            h.set_text(f"{dt.hour:02d}"); time.sleep(0.3)
            m.set_text(f"{dt.minute:02d}"); time.sleep(0.3)
        self._wait_click("OK (horário)", resourceId="android:id/button1")
        time.sleep(0.6)
        # --- Concluir do overlay ---
        return self._wait_click("Concluir (agendar)", resourceId=_rid("bb_primary_action_container"))

    def set_datetime_roda(self, dt) -> bool:
        """Estilo RODA: 3 numberpicker_input por índice (0=data,1=hora,2=minuto).
        NumberPicker aceita set_text de forma irregular → tenta set_text e valida."""
        pk = self.d(resourceId=_rid("numberpicker_input"))
        if not pk.exists:
            return False
        # hora e minuto por texto direto (numberpicker costuma aceitar em EditText)
        try:
            els = list(self.d(resourceId=_rid("numberpicker_input")))
        except Exception:
            els = []
        if len(els) >= 3:
            try:
                els[1].set_text(f"{dt.hour:02d}")
                els[2].set_text(f"{dt.minute:02d}")
            except Exception as exc:
                self.log(f"⚠ set_text da roda falhou: {exc} (a validar/ajustar p/ swipe)")
        # data (índice 0) é a mais complexa (texto tipo 'qua., 22 de jul.') → deixar
        # no dia atual por ora; ajustar depois com leitura+swipe se necessário.
        return self._wait_click("Concluir (agendar)", resourceId=_rid("bb_primary_action_container"))

    def set_schedule(self, dt) -> bool:
        style = self.detect_picker()
        self.log(f"• estilo do seletor detectado: {style or '???'}")
        if style == "relogio":
            return self.set_datetime_relogio(dt)
        if style == "roda":
            return self.set_datetime_roda(dt)
        self.log("⚠ nenhum overlay de data/hora reconhecido")
        return False

    def submit(self, schedule: bool = True) -> bool:
        """Toca o botão final (share_footer_button): 'Programar' (agendado) ou 'Compartilhar'."""
        return self._wait_click("botão final (Programar/Compartilhar)",
                                resourceId=_rid("share_footer_button"))


# --- orquestração do POST completo -----------------------------------------
def post_flow(serial, account, image_paths, caption="", collaborators=None,
              when=None, publish=False, report=None) -> dict:
    """Fluxo completo de postagem/agendamento. publish=False PARA antes do botão
    final (Programar/Compartilhar) — modo seguro de teste. when=datetime (agendar)
    ou None (imediato)."""
    r = {"ok": False, "stage": "", "style": "", "error": ""}
    drv = IGDriver(serial, report=report)
    try:
        drv.connect()
        r["stage"] = "push";       drv.push_carousel(image_paths)
        r["stage"] = "abrir";      drv.open_app(fresh=True)
        drv.go_to_profile()
        if account:
            drv.ensure_account(account)
        r["stage"] = "criar";      drv.open_create_post(); time.sleep(2)
        r["stage"] = "selecionar"; drv.select_carousel(len(image_paths))
        r["stage"] = "avancar1";   drv.advance_selection(); time.sleep(1.5)
        r["stage"] = "taxa";       drv.set_aspect_portrait(); time.sleep(1)
        r["stage"] = "avancar2";   drv.advance_edit(); time.sleep(2)
        r["stage"] = "legenda";    drv.set_caption(caption)
        if collaborators:
            r["stage"] = "colab";  drv.add_collaborators(collaborators); time.sleep(1)
        if when is not None:
            r["stage"] = "maisopcoes"; drv.open_more_options(); time.sleep(1.5)
            r["stage"] = "toggle";     drv.toggle_schedule(); time.sleep(1.5)
            r["style"] = drv.detect_picker()
            r["stage"] = "datahora";   drv.set_schedule(when); time.sleep(1.5)
        if publish:
            r["stage"] = "submit";     drv.submit(schedule=when is not None)
            drv.log("✅ POST enviado")
        else:
            drv.log("⏸ PARADO antes do botão final (modo seguro — nada publicado)")
        r["ok"] = True
    except Exception as exc:
        r["error"] = str(exc)
        drv.log(f"ERRO no estágio '{r['stage']}': {exc}")
    return r


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
