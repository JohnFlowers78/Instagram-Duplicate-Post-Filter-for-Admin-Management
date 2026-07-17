import json
import os
import re
import shutil
import tempfile
import threading
import tkinter as tk
import uuid
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageDraw, ImageTk

import config
import crossaccount
import cta
import dedup
import downloader
import feedbot
import feedinbox
import organizer
import waitqueue
from paths import DATA_DIR, ASSETS_DIR

HISTORY_FILE  = DATA_DIR   / "history.json"
ICON_WINDOW   = ASSETS_DIR / "icon.ico"        # icone da janela + taskbar (ico)
LOGO_HEADER   = ASSETS_DIR / "logo_header.png" # logo no header do app (png)
THUMB_SIZE = (64, 64)
ICON_PX = 13

STEPS = [
    "Verificando configuracoes...",
    "Preparando pasta do dia...",
    "Baixando midias do snapinsta.to...",
    "Verificando repeticoes...",
    "Salvando arquivos na pasta de envio...",
    "Concluido!",
]

# ---------------------------------------------------------------------------
# Paleta de cores
# ---------------------------------------------------------------------------

# Dois temas. _apply_palette() copia o escolhido para os nomes globais usados
# em toda a UI; trocar de tema reaplica a paleta e reconstroi os widgets.
_LIGHT = {
    "BG": "#EEEAE5",     # fundo principal — bege quente
    "PANEL": "#FFFFFF",  # cartoes/paineis — branco
    "INNER": "#F7F5F2",  # fundos internos
    "BORDER": "#D9D4CE", # bordas sutis
    "TXT_H": "#1C1917",  # texto principal — quase preto
    "TXT_B": "#44403C",  # corpo — cinza escuro quente
    "TXT_M": "#9C9590",  # texto secundario — cinza medio
    "ACCENT": "#0D9488", # teal vibrante — cor de destaque
    "OK_BG": "#DCFCE7", "OK_FG": "#14532D",   # sucesso
    "ERR_BG": "#FEE2E2", "ERR_FG": "#991B1B", # erro
    "BPF": "#1C1917", "BPT": "#FFFFFF", "BPA": "#374151",  # botao primario (fundo/texto/hover)
    "BSF": "#E8E4DF", "BST": "#1C1917",       # botao secundario
    "BDF": "#DC2626", "BDT": "#FFFFFF",       # botao perigo
    "BGF": "#16A34A", "BGT": "#FFFFFF",       # botao verde
    "ICON_RGB": (100, 100, 100, 255),         # cor dos icones desenhados
}
_DARK = {
    "BG": "#1C1A17",     # fundo principal — quase preto quente
    "PANEL": "#262220",  # cartoes/paineis
    "INNER": "#2F2A26",  # fundos internos
    "BORDER": "#3C3631", # bordas
    "TXT_H": "#F4F0EB",  # texto principal — quase branco
    "TXT_B": "#CFC9C1",  # corpo
    "TXT_M": "#928B84",  # texto secundario
    "ACCENT": "#2DD4BF", # teal mais claro para fundo escuro
    "OK_BG": "#14532D", "OK_FG": "#DCFCE7",
    "ERR_BG": "#7F1D1D", "ERR_FG": "#FEE2E2",
    "BPF": "#EDE9E3", "BPT": "#1C1917", "BPA": "#FFFFFF",  # primario claro sobre fundo escuro
    "BSF": "#33302B", "BST": "#F4F0EB",
    "BDF": "#DC2626", "BDT": "#FFFFFF",
    "BGF": "#16A34A", "BGT": "#FFFFFF",
    "ICON_RGB": (165, 160, 155, 255),
}


def _apply_palette(name: str) -> None:
    globals().update(_DARK if name == "dark" else _LIGHT)


_apply_palette("light")  # padrao no import; __init__ reaplica conforme a config

QUEUE_W = 350        # largura do painel Salvos/Listas quando aberto
QUEUE_MIN_W = 350    # largura MINIMA do painel aberto (nunca menor que isso)
MAIN_MIN_W = 536     # largura MINIMA da area principal (abas) com o painel aberto
WIN_MIN_W = 900      # largura minima da janela desde a abertura do app
WIN_MIN_H = 700      # altura minima da janela
GRID_GAP = 14        # respiro da grade de colecoes: borda esq = vao central = borda dir
CROSS_ROW_H = 150    # altura fixa de cada cartao na lista virtualizada do Entre Contas
CROSS_OVERSCAN = 3   # cartoes renderizados alem da area visivel (cada lado)
FEED_ROW_H = 560     # altura fixa de cada publicacao no Feed Especial (virtualizado)
FEED_IMG = 400       # lado da capa quadrada no Feed Especial
FEED_OVERSCAN = 2    # publicacoes renderizadas alem da area visivel (cada lado)

FONT_H  = ("Segoe UI", 10, "bold")
FONT_SH = ("Segoe UI", 9, "bold")
FONT_B  = ("Segoe UI", 9)
FONT_S  = ("Segoe UI", 8)
FONT_M  = ("Segoe UI", 8)
FONT_LBL = ("Segoe UI", 7, "bold")   # rotulos de secao uppercase


# ---------------------------------------------------------------------------
# Icones PIL
# ---------------------------------------------------------------------------

def _make_icon(draw_fn, size: int = ICON_PX) -> ImageTk.PhotoImage:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(img), size)
    return ImageTk.PhotoImage(img)


def _icon_eye(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = ICON_RGB
        d.arc([0, s // 4, s - 1, s * 3 // 4 - 1], start=180, end=360, fill=c, width=1)
        d.arc([0, s // 4, s - 1, s * 3 // 4 - 1], start=0, end=180, fill=c, width=1)
        r = max(1, s // 6)
        cx, cy = s // 2, s // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return _make_icon(draw, size)


def _icon_heart(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = ICON_RGB
        h = s // 2
        d.arc([0, 0, h, h], start=180, end=360, fill=c, width=1)
        d.arc([h - 2, 0, s - 1, h], start=180, end=360, fill=c, width=1)
        q = h // 2
        d.line([(0, q), (s // 2, s - 1)], fill=c, width=1)
        d.line([(s - 1, q), (s // 2, s - 1)], fill=c, width=1)
    return _make_icon(draw, size)


def _icon_bubble(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = ICON_RGB
        tail = max(2, s // 4)
        d.ellipse([0, 0, s - 1, s - 1 - tail], outline=c, width=1)
        d.polygon([(1, s - tail - 1), (0, s - 1), (tail + 1, s - tail - 1)], fill=c)
    return _make_icon(draw, size)


def _icon_copy(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = ICON_RGB
        off = s // 4
        d.rectangle([off, 0, s - 1, s - 1 - off], outline=c, width=1)
        d.rectangle([0, off, s - 1 - off, s - 1], outline=c, width=1)
    return _make_icon(draw, size)


# ---------------------------------------------------------------------------
# Persistencia do historico
# ---------------------------------------------------------------------------

def _load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(entries: list) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Aplicacao principal
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.cfg = config.load_config()
        _apply_palette(self.cfg.get("theme", "light"))  # antes de qualquer cor

        self.title("Filtro de Repetidas - Instagram")
        self.geometry(f"{WIN_MIN_W}x760")
        self.minsize(WIN_MIN_W, WIN_MIN_H)
        self.resizable(True, True)
        self.configure(bg=BG)

        self._thumb_refs: list = []
        self._result_popup = None
        self._log_counter = 0
        self._logo_photo = None  # referencia para evitar GC do PhotoImage

        # Icone da janela + taskbar do Windows
        if ICON_WINDOW.exists():
            try:
                self.iconbitmap(str(ICON_WINDOW))
            except Exception:
                pass

        self._make_icons()

        # Variaveis de configuracao (aba Configuracoes)
        self._var_counter = tk.BooleanVar(value=self.cfg.get("include_day_counter", True))
        self._var_initial = tk.BooleanVar(value=self.cfg.get("include_person_initial", True))
        self._var_letter  = tk.StringVar(value=self.cfg.get("person_initial", "Z"))
        self._var_slots   = tk.StringVar(value=str(self.cfg.get("slots_per_day", 4)))
        self._var_thresh  = tk.StringVar(value=str(self.cfg.get("hash_threshold", 5)))
        self._var_theme   = tk.StringVar(value=self.cfg.get("theme", "light"))
        self._theme_applied = self.cfg.get("theme", "light")

        self._setup_styles()
        self._build_ui()

        # Traces depois do build para que _lbl_preview ja exista
        self._var_counter.trace_add("write", self._update_preview)
        self._var_initial.trace_add("write", self._on_initial_var_change)
        self._var_letter.trace_add("write", self._update_preview)

        self._update_preview()
        self._refresh_db_folder_label()
        self._refresh_src_folder_label()
        self._reload_history_panel()

    def _make_icons(self):
        """(Re)cria os icones desenhados com a cor do tema atual (ICON_RGB)."""
        self._ico_eye    = _icon_eye()
        self._ico_heart  = _icon_heart()
        self._ico_bubble = _icon_bubble()
        self._ico_copy   = _icon_copy()

    # ------------------------------------------------------------------
    # Estilos ttk
    # ------------------------------------------------------------------

    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=BORDER,
            background=ACCENT,
            thickness=5,
            borderwidth=0,
        )
        s.configure(
            "TScrollbar",
            background=BORDER,
            troughcolor=INNER,
            width=7,
            arrowsize=7,
            bordercolor=INNER,
            relief="flat",
        )
        s.map("TScrollbar", background=[("active", TXT_M)])

    # ------------------------------------------------------------------
    # Construcao da UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._tab_btns  = {}
        self._tab_inds  = {}
        self._tab_pages = {}
        self._tab_active = None
        self._queue_open = False
        self._queue_w = QUEUE_W
        self._hist_inners = []   # inners de historico (compartilhado entre abas)
        self._hist_headers = []  # cabecalhos (setas + rotulo do dia) por painel
        self._hist_page = 0      # 0 = dia mais recente ("Lista de Publicações do Dia")

        # Corpo: coluna esquerda (app) + painel direito retratil (fila de espera)
        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill="both", expand=True)

        self._left = tk.Frame(self._body, bg=BG)
        self._left.pack(side="left", fill="both", expand=True)

        self._queue_panel = tk.Frame(self._body, bg=BG, width=QUEUE_W)
        self._queue_panel.pack_propagate(False)
        self._build_queue_panel(self._queue_panel)

        # Barra de abas
        tab_bar = tk.Frame(self._left, bg=PANEL)
        tab_bar.pack(fill="x")

        # Logo no canto esquerdo da barra de abas
        if LOGO_HEADER.exists():
            try:
                _img = Image.open(LOGO_HEADER).resize((30, 30), Image.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(_img)
                tk.Label(tab_bar, image=self._logo_photo, bg=PANEL,
                         padx=8, pady=4).pack(side="left")
            except Exception:
                pass

        for key, label in [("feed", "  Feed  "),
                           ("link", "  Filtro por Link  "),
                           ("cross", "  Filtro Entre Contas  "),
                           ("settings", "  Configurações  ")]:
            col = tk.Frame(tab_bar, bg=PANEL)
            col.pack(side="left")
            btn = tk.Button(
                col, text=label,
                font=FONT_B, bg=PANEL, fg=TXT_M,
                relief="flat", bd=0,
                padx=6, pady=10,
                cursor="hand2",
                activebackground=PANEL, activeforeground=TXT_H,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack()
            ind = tk.Frame(col, height=2, bg=PANEL)
            ind.pack(fill="x")
            self._tab_btns[key] = btn
            self._tab_inds[key] = ind

        # Botao de abrir/fechar a fila de espera (seta no canto superior direito)
        self._btn_queue_toggle = tk.Button(
            tab_bar, text="❯", font=("Segoe UI", 13, "bold"),
            bg=PANEL, fg=ACCENT, relief="flat", bd=0,
            padx=12, pady=6, cursor="hand2",
            activebackground=INNER, activeforeground=ACCENT,
            command=self._toggle_queue_panel,
        )
        self._btn_queue_toggle.pack(side="right", padx=(0, 6))

        tk.Frame(self._left, bg=BORDER, height=1).pack(fill="x")

        # Paginas de conteudo
        for key, build_fn in [
            ("feed",     self._build_feed_tab),
            ("link",     self._build_link_tab),
            ("cross",    self._build_cross_tab),
            ("settings", self._build_settings_tab),
        ]:
            page = tk.Frame(self._left, bg=BG)
            self._tab_pages[key] = page
            build_fn(page)

        self._switch_tab("link")

    def _switch_tab(self, name: str):
        for k in self._tab_pages:
            self._tab_pages[k].pack_forget()
            self._tab_btns[k].configure(fg=TXT_M, font=FONT_B)
            self._tab_inds[k].configure(bg=PANEL)
        self._tab_pages[name].pack(fill="both", expand=True)
        self._tab_btns[name].configure(fg=ACCENT, font=FONT_SH)
        self._tab_inds[name].configure(bg=ACCENT)
        self._tab_active = name
        # O painel direito e contextual: fila de links x listas entre contas
        if hasattr(self, "_queue_panel"):
            self._refresh_queue_panel_context()
        if name == "feed" and hasattr(self, "_feed_inner"):
            self._reload_feed_view()

    # ------------------------------------------------------------------
    # Chave seletora de modo (usar agora / fila de espera)
    # ------------------------------------------------------------------

    def _set_mode(self, mode: str):
        self._var_mode = mode
        for key, b in self._mode_btns.items():
            if key == mode:
                b.configure(bg=ACCENT, fg="#FFFFFF",
                            activebackground=ACCENT, activeforeground="#FFFFFF")
            else:
                b.configure(bg=INNER, fg=TXT_M,
                            activebackground=INNER, activeforeground=TXT_B)
        # Linha 'Salvar em:' (colecao de destino) — so no modo fila
        row = getattr(self, "_q_dest_row", None)
        if row is not None:
            try:
                if mode == "queue":
                    self._populate_q_dest_combo()
                    if not row.winfo_ismapped():
                        row.pack(fill="x", pady=(0, 8), after=self._mode_row)
                else:
                    row.pack_forget()
            except tk.TclError:
                pass
        # btn_start pode ainda nao existir (durante o build) ou apontar para um
        # widget ja destruido (durante a reconstrucao de tema) — protege ambos.
        btn = getattr(self, "btn_start", None)
        if btn is not None:
            try:
                btn.config(text="Adicionar à Fila" if mode == "queue" else "Iniciar")
            except tk.TclError:
                pass

    def _populate_q_dest_combo(self, select_id=None):
        """Preenche o 'Salvar em:' — Salvos (geral), Salvos + cada coleção, nova."""
        cols = waitqueue.load_collections()
        prev_id = None
        cur = self._q_dest_combo.current()
        if 0 <= cur < len(self._q_dest_ids):
            prev_id = self._q_dest_ids[cur]
        self._q_dest_ids = [None] + [c.get("id") for c in cols] + ["__new__"]
        values = (["Salvos (geral)"]
                  + [f"Salvos + {c.get('name', '?')}" for c in cols]
                  + ["+ Nova coleção…"])
        self._q_dest_combo.config(values=values)
        target = select_id if select_id is not None else prev_id
        idx = self._q_dest_ids.index(target) if target in self._q_dest_ids else 0
        if self._q_dest_ids[idx] == "__new__":
            idx = 0
        self._q_dest_combo.current(idx)

    def _refresh_q_dest_combo_safe(self):
        """Repopula o 'Salvar em:' apos criar/renomear/apagar colecoes."""
        if hasattr(self, "_q_dest_combo") and getattr(self, "_var_mode", "") == "queue":
            try:
                self._populate_q_dest_combo()
            except tk.TclError:
                pass

    def _on_q_dest_selected(self, event=None):
        idx = self._q_dest_combo.current()
        if not (0 <= idx < len(self._q_dest_ids)):
            return
        if self._q_dest_ids[idx] == "__new__":
            name = self._ask_text("Nova Coleção", "Nome da coleção:")
            if name:
                col = waitqueue.create_collection(name)
                self._populate_q_dest_combo(select_id=col.get("id"))
                # grade de colecoes aberta no painel? atualiza na hora
                if (getattr(self, "_tab_active", "link") == "link"
                        and getattr(self, "_q_view_mode", "main") == "grid"):
                    self._reload_queue_panel()
            else:
                self._populate_q_dest_combo()   # cancelou → volta pro Salvos (geral)

    # ------------------------------------------------------------------
    # Tema (claro / escuro)
    # ------------------------------------------------------------------

    def _set_theme(self, name: str):
        if name not in ("light", "dark"):
            name = "light"
        self._var_theme.set(name)
        if self.cfg.get("theme", "light") == name and getattr(self, "_theme_applied", None) == name:
            return
        self.cfg["theme"] = name
        config.save_config(self.cfg)
        self._rebuild_for_theme(name)

    def _rebuild_for_theme(self, name: str):
        """Reaplica a paleta e reconstroi toda a UI (sem reiniciar o app)."""
        _apply_palette(name)
        self._theme_applied = name
        saved_mode = getattr(self, "_var_mode", "use")
        saved_qw = getattr(self, "_queue_w", QUEUE_W)
        queue_was_open = getattr(self, "_queue_open", False)

        self.configure(bg=BG)
        self._make_icons()           # icones na cor do novo tema
        for child in self.winfo_children():
            child.destroy()          # remove a UI atual inteira
        self._setup_styles()         # recolore progressbar/scrollbar (ttk)
        self._build_ui()
        self._queue_w = saved_qw     # preserva a largura customizada da fila

        self._set_mode(saved_mode)
        self._update_preview()
        self._refresh_db_folder_label()
        self._refresh_src_folder_label()
        self._reload_history_panel()
        self._switch_tab("settings")  # mantem o usuario na aba de configuracoes
        if queue_was_open:
            self._toggle_queue_panel()

    # ------------------------------------------------------------------
    # Divisoria arrastavel entre LOGs e Historico (bandeija)
    # ------------------------------------------------------------------

    def _divider_drag_start(self, event):
        self._drag_y0 = event.y_root
        self._drag_h0 = self._logs_holder.winfo_height()
        self._logs_pending_h = None
        self._logs_resize_scheduled = False

    def _divider_drag(self, event):
        delta = event.y_root - self._drag_y0
        new_h = self._drag_h0 + delta
        max_h = self._split.winfo_height() - 130  # espaco minimo para o historico
        new_h = max(60, min(new_h, max(60, max_h)))
        # Coalesce: guarda o alvo e aplica no maximo 1x por quadro (~60fps),
        # evitando acumulo de relayouts quando os eventos de movimento sao densos.
        self._logs_pending_h = int(new_h)
        if not self._logs_resize_scheduled:
            self._logs_resize_scheduled = True
            self.after(16, self._apply_logs_resize)

    def _apply_logs_resize(self):
        self._logs_resize_scheduled = False
        if self._logs_pending_h is not None:
            try:
                self._logs_holder.configure(height=self._logs_pending_h)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Painel retratil da fila de espera
    # ------------------------------------------------------------------

    def _toggle_queue_panel(self):
        if self._queue_open:
            w = self._queue_panel.winfo_width()
            self._queue_panel.pack_forget()
            self._btn_queue_toggle.config(text="❯")
            self._queue_open = False
            new_w = max(self.winfo_width() - w, self.minsize()[0])
        else:
            # O painel abre SEMPRE com pelo menos a largura minima
            self._queue_w = max(getattr(self, "_queue_w", QUEUE_W), QUEUE_MIN_W)
            self._queue_panel.configure(width=self._queue_w)
            self._queue_panel.pack(side="right", fill="y")
            self._btn_queue_toggle.config(text="❮")
            self._queue_open = True
            self._refresh_queue_panel_context()
            new_w = self.winfo_width() + self._queue_w
        self.geometry(f"{new_w}x{self.winfo_height()}")

    def _queue_drag_start(self, event):
        self._qdrag_x0 = event.x_root
        self._qdrag_w0 = self._queue_panel.winfo_width()
        self._q_pending_w = None
        self._q_resize_scheduled = False

    def _queue_drag(self, event):
        # Puxar para a esquerda (x_root diminui) aumenta a largura da fila
        delta = self._qdrag_x0 - event.x_root
        new_w = self._qdrag_w0 + delta
        # A bandeja respeita os MINIMOS dos dois lados: painel >= QUEUE_MIN_W e
        # area principal >= MAIN_MIN_W. Na janela em tamanho minimo ela trava;
        # para ganhar folga e so alargar a janela do app.
        min_w = QUEUE_MIN_W
        max_w = self.winfo_width() - MAIN_MIN_W
        new_w = max(min_w, min(new_w, max(min_w, max_w)))
        self._queue_w = new_w
        # Coalesce em ~60fps (ver _divider_drag): mais leve e sem engasgo
        self._q_pending_w = int(new_w)
        if not self._q_resize_scheduled:
            self._q_resize_scheduled = True
            self.after(16, self._apply_q_resize)

    def _apply_q_resize(self):
        self._q_resize_scheduled = False
        if self._q_pending_w is not None:
            try:
                self._queue_panel.configure(width=self._q_pending_w)
            except tk.TclError:
                pass

    def _refresh_queue_panel_context(self):
        """Painel direito e contextual: fila de links (aba Filtro por Link) ou
        listas entre contas (aba Filtro Entre Contas)."""
        if not hasattr(self, "_queue_inner"):
            return
        if getattr(self, "_tab_active", "link") == "cross":
            self._q_title.config(text="LISTAS ENTRE CONTAS")
            self._q_metrics_btn.pack_forget()
            self._q_clear_btn.pack_forget()
            self._q_seg.pack_forget()
            self._q_col_hdr.pack_forget()
            if not self._q_controls.winfo_ismapped():
                self._q_controls.pack(fill="x", after=self._q_hdr)
            self._repair_cross_used_flags(crossaccount.get_active())
            self._populate_cross_combo()
            self._render_cross_list(reset_scroll=True)
            self._start_cross_ocr(crossaccount.get_active())
        else:
            self._q_title.config(text="SALVOS")
            if not self._q_metrics_btn.winfo_ismapped():
                self._q_metrics_btn.pack(side="right")
            if not self._q_clear_btn.winfo_ismapped():
                self._q_clear_btn.pack(side="right", padx=(0, 6))
            self._q_controls.pack_forget()
            if not self._q_seg.winfo_ismapped():
                self._q_seg.pack(fill="x", after=self._q_hdr, pady=(0, 4))
            self._reload_queue_panel()

    # ------------------------------------------------------------------
    # Painel: listas do Filtro Entre Contas
    # ------------------------------------------------------------------

    def _populate_cross_combo(self):
        summary = crossaccount.lists_summary()
        self._q_list_ids = [lid for (lid, _n, _c) in summary]
        values = [f"{n} ({c})" for (_l, n, c) in summary]
        self._q_list_combo.config(values=values)
        active = crossaccount.get_active()
        if active in self._q_list_ids:
            self._q_list_combo.current(self._q_list_ids.index(active))
        elif values:
            self._q_list_combo.current(0)
            crossaccount.set_active(self._q_list_ids[0])
        else:
            self._q_list_var.set("")

    def _on_cross_list_selected(self, event=None):
        idx = self._q_list_combo.current()
        if 0 <= idx < len(self._q_list_ids):
            crossaccount.set_active(self._q_list_ids[idx])
            self._repair_cross_used_flags(self._q_list_ids[idx])
            self._render_cross_list(reset_scroll=True)
            self._start_cross_ocr(self._q_list_ids[idx])

    def _repair_cross_used_flags(self, list_id: str):
        """Auto-reparo: item marcado 'used' que NAO tem registro correspondente no
        Historico (ex.: pelo bug de chave nao-unica) volta a ficar disponivel."""
        if not list_id:
            return
        used_ids = {
            (e.get("origin") or {}).get("item_id")
            for e in _load_history() if (e.get("origin") or {}).get("origin") == "cross"
        }
        data = crossaccount.load()
        lst = crossaccount.get_list(list_id, data)
        if not lst:
            return
        changed = False
        for it in lst.get("items", []):
            if it.get("used") and it.get("id") not in used_ids:
                it["used"] = False
                changed = True
        if changed:
            crossaccount.save(data)

    def _render_cross_list(self, reset_scroll: bool = False):
        # Interrompe qualquer animacao da fila de links e limpa o inner
        self._q_drag = None
        self._q_state = []
        for w in self._queue_inner.winfo_children():
            w.destroy()
        self._cross_rows = {}   # {index: cartao} atualmente renderizados
        active = crossaccount.get_active()
        lst = crossaccount.get_list(active) if active else None
        self._cross_list_id = active
        all_items = list(lst.get("items")) if lst and lst.get("items") else []
        self._cross_items = self._apply_cross_view(all_items)
        if hasattr(self, "_cf_count_lbl"):
            try:
                self._cf_count_lbl.config(text=f"{len(self._cross_items)} de {len(all_items)}")
            except tk.TclError:
                pass
        if not all_items:
            self._queue_inner.configure(height=80)
            tk.Label(
                self._queue_inner,
                text="Nenhuma lista.\nAnalise uma conta na aba\n'Filtro Entre Contas'.",
                fg=TXT_M, font=FONT_B, bg=PANEL, wraplength=240, justify="center",
            ).place(x=12, y=16)
            return
        if not self._cross_items:
            self._queue_inner.configure(height=80)
            tk.Label(
                self._queue_inner,
                text="Nenhuma publicação passa\nnos filtros atuais.",
                fg=TXT_M, font=FONT_B, bg=PANEL, wraplength=240, justify="center",
            ).place(x=12, y=16)
            return
        # Virtualizacao: o inner tem a altura total; so os cartoes visiveis (+ margem)
        # sao criados de verdade — abrir a lista fica leve mesmo com centenas de itens.
        self._queue_inner.configure(height=len(self._cross_items) * CROSS_ROW_H + 4)
        if reset_scroll:
            self._queue_canvas.yview_moveto(0)
        self._cross_virtual_update()

    # --- Filtros e ordenacao da lista (a logica fica em crossaccount) ---

    _CF_SORT_MAP = {
        "Ordem original": "orig",
        "Dia ↑ (antigas primeiro)": "day_asc",
        "Dia ↓ (recentes primeiro)": "day_desc",
        "Disponíveis primeiro": "avail_first",
        "Repetidas/utilizadas primeiro": "gray_first",
        "CTA (Comentar primeiro)": "cta",
    }
    _CF_STATUS_MAP = {
        "Todas": "all",
        "Disponíveis": "available",
        "Repetidas": "duplicate",
        "Já utilizadas": "used",
    }
    _CF_CTA_MAP = {
        "Todos": "all",
        "Comentar": "comentar",
        "Guardar": "guardar",
        "Seguir": "seguir",
        "Link na bio": "link na bio",
        "Sem CTA": "none",
    }

    def _cf_day_bound(self, var) -> "int | None":
        try:
            v = var.get().strip()
            return int(v) if v else None
        except (ValueError, tk.TclError):
            return None

    def _apply_cross_view(self, items: list) -> list:
        """Aplica os filtros combinados + ordenacao escolhidos na barra do painel."""
        if not hasattr(self, "_cf_sort"):
            return list(items)
        view = crossaccount.filter_items(
            items,
            status=self._CF_STATUS_MAP.get(self._cf_status.get(), "all"),
            cta=self._CF_CTA_MAP.get(self._cf_cta.get(), "all"),
            trigger=self._cf_trigger.get(),
            day_min=self._cf_day_bound(self._cf_day_min),
            day_max=self._cf_day_bound(self._cf_day_max),
        )
        return crossaccount.sort_items(
            view, self._CF_SORT_MAP.get(self._cf_sort.get(), "orig")
        )

    def _cross_view_uses_cta(self) -> bool:
        if not hasattr(self, "_cf_cta"):
            return False
        return (
            self._cf_cta.get() != "Todos"
            or bool(self._cf_trigger.get().strip())
            or self._CF_SORT_MAP.get(self._cf_sort.get()) == "cta"
        )

    def _schedule_cross_rerender(self):
        """Re-render coalescido (1 apos a rajada) — evita piscar durante o OCR."""
        if getattr(self, "_cross_rr_after", None):
            try:
                self.after_cancel(self._cross_rr_after)
            except Exception:
                pass
        def fire():
            self._cross_rr_after = None
            if getattr(self, "_tab_active", "") == "cross":
                self._render_cross_list()
        self._cross_rr_after = self.after(1000, fire)

    def _on_cross_filter_change(self, event=None):
        if getattr(self, "_tab_active", "") == "cross":
            self._render_cross_list(reset_scroll=True)

    def _on_cross_filter_typed(self, event=None):
        """Campos digitados (gatilho/dias): aplica com debounce de 350ms."""
        if getattr(self, "_cf_typed_after", None):
            try:
                self.after_cancel(self._cf_typed_after)
            except Exception:
                pass
        self._cf_typed_after = self.after(350, self._on_cross_filter_change)

    def _clear_cross_filters(self):
        self._cf_sort.set("Ordem original")
        self._cf_status.set("Todas")
        self._cf_cta.set("Todos")
        self._cf_trigger.set("")
        self._cf_day_min.set("")
        self._cf_day_max.set("")
        self._on_cross_filter_change()

    def _cross_virtual_update(self):
        """Cria apenas os cartoes na area visivel (+ overscan) e destroi os que sairam."""
        if not getattr(self, "_cross_items", None) or not hasattr(self, "_cross_rows"):
            return
        canvas = self._queue_canvas
        try:
            top = max(0.0, canvas.canvasy(0))
        except Exception:
            top = 0.0
        vh = canvas.winfo_height() or 1
        n = len(self._cross_items)
        i0 = max(0, int(top // CROSS_ROW_H) - CROSS_OVERSCAN)
        i1 = min(n - 1, int((top + vh) // CROSS_ROW_H) + CROSS_OVERSCAN)
        want = set(range(i0, i1 + 1))
        have = set(self._cross_rows.keys())
        for i in have - want:
            try:
                self._cross_rows[i].destroy()
            except Exception:
                pass
            del self._cross_rows[i]
        for i in want - have:
            row = self._build_cross_row(self._cross_list_id, self._cross_items[i])
            row.place(x=4, y=i * CROSS_ROW_H, relwidth=1, width=-8)
            self._cross_rows[i] = row

    # --- Deteccao de CTA em segundo plano (OCR) ---

    def _start_cross_ocr(self, list_id: str):
        """Dispara o OCR dos CTAs da lista em segundo plano: itens disponiveis
        primeiro, usados/repetidos por ultimo, e so os que ainda nao tem CTA."""
        if not list_id or not cta.available():
            return
        self._cross_ocr_gen = getattr(self, "_cross_ocr_gen", 0) + 1
        gen = self._cross_ocr_gen
        threading.Thread(
            target=self._cross_ocr_worker, args=(list_id, gen), daemon=True
        ).start()

    def _cross_ocr_worker(self, list_id: str, gen: int):
        lst = crossaccount.get_list(list_id)
        if not lst:
            return

        def prio(it):
            if it.get("used"):
                return 2
            if it.get("duplicate"):
                return 1
            return 0  # disponiveis primeiro

        items = lst.get("items", [])
        done = sum(1 for it in items if it.get("cta"))
        pend = sorted([it for it in items if not it.get("cta")], key=prio)
        if not pend:
            return  # tudo analisado — sem barulho no LOG a cada troca de aba

        n_avail = sum(1 for it in pend if prio(it) == 0)
        n_gray = len(pend) - n_avail
        self._cross_log(
            f"CTA: {done} já analisada(s) · {len(pend)} pendente(s) — "
            f"{n_avail} disponível(is) primeiro, depois {n_gray} repetida(s)/utilizada(s)."
        )
        gray_started = False
        for i, it in enumerate(pend, start=1):
            if gen != getattr(self, "_cross_ocr_gen", gen):
                return  # cancelado (troca de lista / novo import / fechou)
            if not gray_started and prio(it) > 0:
                gray_started = True
                self._cross_log("CTA: disponíveis concluídas — agora as repetidas/já utilizadas…")
            status = ("já utilizada" if it.get("used")
                      else "repetida" if it.get("duplicate") else "disponível")
            label = it.get("folder") or "?"
            self._cross_log(f"  CTA {i}/{len(pend)}: analisando [{label}] ({status})…")
            try:
                result = cta.detect_cta(crossaccount.item_images(it))
            except Exception:
                result = "não detectada"
            crossaccount.set_item_field(list_id, it["id"], "cta", result)
            self._cross_log(f"  CTA {i}/{len(pend)}: [{label}] → {result}")
            self.after(0, lambda iid=it["id"], c=result: self._apply_cta(iid, c))
        if gen == getattr(self, "_cross_ocr_gen", gen):
            self._cross_log("CTA: análise concluída ✔")

    def _apply_cta(self, item_id: str, cta_text: str):
        """Atualiza SO o item que mudou (reativo): mexe no dado em memoria e, se o
        cartao estiver renderizado, so reconfigura o rotulo da CTA — sem re-render,
        sem piscar."""
        items = getattr(self, "_cross_items", [])
        idx = None
        for i, it in enumerate(items):
            if it.get("id") == item_id:
                it["cta"] = cta_text
                idx = i
                break
        if idx is None:
            return
        row = getattr(self, "_cross_rows", {}).get(idx)
        lbl = getattr(row, "_cta_label", None) if row is not None else None
        if lbl is not None:
            good = bool(cta_text) and cta_text != "não detectada"
            try:
                lbl.config(text=f"CTA: {cta_text}", fg=(ACCENT if good else TXT_M))
            except Exception:
                pass
        # Se a visao atual depende do CTA (filtro/gatilho/ordem), o item pode entrar
        # ou sair da lista — re-render coalescido para nao piscar a cada deteccao.
        if self._cross_view_uses_cta():
            self._schedule_cross_rerender()

    def _build_cross_row(self, list_id: str, item: dict):
        gray = bool(item.get("used")) or bool(item.get("duplicate"))
        row_outer = tk.Frame(self._queue_inner, bg=BORDER, padx=1, pady=1)
        row = tk.Frame(row_outer, bg=PANEL, padx=8, pady=8)
        row.pack(fill="both", expand=True)

        top = tk.Frame(row, bg=PANEL)
        top.pack(fill="x")
        thumb_frame = tk.Frame(top, bg=INNER, width=THUMB_SIZE[0] + 4, height=THUMB_SIZE[1] + 4)
        thumb_frame.pack(side="left", padx=(0, 8))
        thumb_frame.pack_propagate(False)
        thumb_path = item.get("thumbnail", "")
        loaded = False
        if thumb_path and Path(thumb_path).exists():
            try:
                img = Image.open(thumb_path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                if gray:
                    img = img.convert("L").convert("RGB")  # cinza = indisponivel
                photo = ImageTk.PhotoImage(img)
                row_outer._photo = photo   # ref presa ao cartao (liberada ao destrui-lo)
                tk.Label(thumb_frame, image=photo, bg=INNER).pack(expand=True)
                loaded = True
            except Exception:
                pass
        if not loaded:
            tk.Label(thumb_frame, text="[sem\nimagem]", fg=TXT_M, font=FONT_M,
                     justify="center", bg=INNER).pack(expand=True)

        info = tk.Frame(top, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=item.get("folder") or "publicação", anchor="w",
                 font=FONT_SH, bg=PANEL, fg=(TXT_M if gray else TXT_H)).pack(fill="x")
        if item.get("used"):
            tk.Label(info, text="⚠ Já utilizada (no histórico)", anchor="w",
                     font=FONT_S, bg=PANEL, fg=BDF).pack(fill="x")
        elif item.get("duplicate"):
            loc = item.get("dup_location", "")
            base = "Repetida (manual)" if item.get("manual") == "dup" else "Repetida"
            txt = f"{base} — em {loc}" if loc else (
                base if item.get("manual") == "dup" else "Repetida (já no destino)")
            tk.Label(info, text=txt, anchor="w", font=FONT_S, bg=PANEL, fg=BDF).pack(fill="x")
        elif item.get("manual") == "ok":
            tk.Label(info, text="✓ Verificada não repetida (manual)", anchor="w",
                     font=FONT_S, bg=PANEL, fg=ACCENT).pack(fill="x")

        # Linha de CTA (preenchida em segundo plano pelo OCR; atualizada em tempo real)
        cta_txt = item.get("cta")
        if cta_txt:
            cta_lbl_text, cta_good = f"CTA: {cta_txt}", (cta_txt != "não detectada")
        elif cta.available():
            cta_lbl_text, cta_good = "CTA: analisando…", False
        else:
            cta_lbl_text, cta_good = "CTA: OCR indisponível", False
        cta_label = tk.Label(info, text=cta_lbl_text, anchor="w", font=FONT_S,
                             bg=PANEL, fg=(ACCENT if cta_good else TXT_M))
        cta_label.pack(fill="x")
        row_outer._cta_label = cta_label

        meta = item.get("meta", {})
        meta_row = tk.Frame(info, bg=PANEL)
        meta_row.pack(fill="x", pady=(2, 0))
        for ico, key in [(self._ico_eye, "views"), (self._ico_heart, "likes"),
                         (self._ico_bubble, "comments")]:
            tk.Label(meta_row, image=ico, bg=PANEL).pack(side="left", padx=(0, 2))
            tk.Label(meta_row, text=meta.get(key, "N/D"), font=FONT_M, bg=PANEL,
                     fg=TXT_B, anchor="w").pack(side="left", padx=(0, 8))

        btns = tk.Frame(row, bg=PANEL)
        btns.pack(fill="x", pady=(8, 0))
        # 'Remover' SO nas repetidas: uma disponivel removida por engano so voltaria
        # reanalisando a conta inteira (o Recarregar NAO ressuscita removidas)
        if item.get("duplicate") and not item.get("used"):
            self._btn(btns, "Remover",
                      lambda: self._remove_cross_item(list_id, item["id"]), "danger_sm").pack(side="right")
        self._btn(btns, "📁", lambda p=item.get("src_path", ""): self._open_folder(p),
                  "secondary_sm").pack(side="right", padx=(0, 4))
        # Marcacao manual: quando o filtro nao reconhece sozinho (ex.: Card Final
        # refeito), o usuario marca/desmarca a repetida na mao. Usados nao mudam.
        if not item.get("used"):
            if item.get("duplicate"):
                self._btn(btns, "Não é Repetida",
                          lambda: self._mark_cross_not_dup(list_id, item["id"]),
                          "secondary_sm").pack(side="left")
            else:
                self._btn(btns, "Utilizar de Próxima",
                          lambda: self._use_cross_item(list_id, item["id"]), "green_sm").pack(side="left")
                self._btn(btns, "É Repetida",
                          lambda: self._mark_cross_dup(list_id, item["id"]),
                          "secondary_sm").pack(side="left", padx=(4, 0))
        return row_outer

    def _mark_cross_dup(self, list_id: str, item_id: str):
        """Marca manualmente como repetida, com pasta/dia opcional de onde ja existe."""
        loc = self._ask_dup_location()
        if loc is None:
            return  # cancelou
        data = crossaccount.load()
        it = crossaccount.find_item(list_id, item_id, data)
        if it is None:
            return
        it["duplicate"] = True
        it["dup_location"] = loc
        it["manual"] = "dup"
        crossaccount.save(data)
        self._render_cross_list()
        self._show_toast("Marcada como repetida (manual).", 3000, OK_BG, OK_FG)

    def _mark_cross_not_dup(self, list_id: str, item_id: str):
        """Desmarca a repetida: volta a ficar disponível e o Recarregar respeita."""
        data = crossaccount.load()
        it = crossaccount.find_item(list_id, item_id, data)
        if it is None:
            return
        it["duplicate"] = False
        it["dup_location"] = ""
        it["manual"] = "ok"
        crossaccount.save(data)
        self._render_cross_list()
        self._show_toast("Marcada como disponível (manual).", 3000, OK_BG, OK_FG)

    def _day_folder_names(self) -> list:
        """Nomes das pastas de dia da Pasta de Destino, mais recentes primeiro."""
        db = self.cfg.get("db_folder")
        names = []
        if db and Path(db).is_dir():
            try:
                for d in Path(db).iterdir():
                    if d.is_dir() and organizer.DIA_FOLDER_RE.match(d.name):
                        names.append(d.name)
            except OSError:
                pass

        def daynum(n):
            m = re.match(r"Dia(\d+)_", n)
            return int(m.group(1)) if m else 0

        names.sort(key=daynum, reverse=True)
        return names

    def _ask_dup_location(self):
        """Dialog opcional: em qual pasta/dia a repetida ja existe.
        Retorna a pasta escolhida/digitada ('' = nao informada) ou None se cancelar."""
        result = [None]

        dlg = tk.Toplevel(self)
        dlg.title("Marcar como Repetida")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.configure(bg=PANEL)

        tk.Label(
            dlg, text="Se souber, indique a pasta/dia onde essa publicação\n"
                      "já existe (opcional — pode deixar em branco):",
            bg=PANEL, fg=TXT_B, font=FONT_B, justify="center", padx=24, pady=(18),
        ).pack()
        combo = ttk.Combobox(dlg, values=self._day_folder_names(), font=FONT_B)
        combo.pack(fill="x", padx=28, pady=(0, 14), ipady=3)

        btn_row = tk.Frame(dlg, bg=PANEL)
        btn_row.pack(pady=(0, 18))

        def do_cancel():
            dlg.destroy()

        def do_confirm():
            result[0] = combo.get().strip()
            dlg.destroy()

        self._btn(btn_row, "CANCELAR", do_cancel, "secondary").pack(side="left", padx=(0, 10))
        self._btn(btn_row, "MARCAR REPETIDA", do_confirm, "danger").pack(side="left")

        self.update_idletasks()
        dlg.update_idletasks()
        w, h = 400, 190
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.wait_window()
        return result[0]

    def _use_cross_item(self, list_id: str, item_id: str):
        db = self.cfg.get("db_folder")
        if not db or not Path(db).is_dir():
            self._show_toast("Selecione a Pasta de Destino primeiro.", 4000, ERR_BG, ERR_FG)
            return
        item = crossaccount.find_item(list_id, item_id)
        if item is None:
            return
        images = crossaccount.item_images(item)
        if not images:
            self._show_toast("Imagens não encontradas na pasta de origem.", 4000, ERR_BG, ERR_FG)
            return
        db_folder = Path(db)
        initial     = self.cfg.get("person_initial", "Z")
        slots       = self.cfg.get("slots_per_day", 4)
        inc_counter = self.cfg.get("include_day_counter", True)
        inc_initial = self.cfg.get("include_person_initial", True)
        day_folder = organizer.ensure_day_folder(db_folder, initial, slots, inc_counter, inc_initial)
        slot = organizer.find_next_empty_slot(day_folder, slots)
        if slot is None:
            self._show_toast(f"Não há pasta livre hoje em '{day_folder.name}'.", 4000, ERR_BG, ERR_FG)
            return
        # cache_hashes=False: o Card Final ainda vai ser refeito (IA) — os hashes
        # da pasta de destino sao recalculados depois, a partir das imagens reais.
        organizer.save_media_to_slot(slot, images, cache_hashes=False)
        # A legenda viaja junto: grava no Legenda.txt da pasta de destino
        caption = (item.get("caption") or "").strip()
        if caption:
            try:
                (slot / "Legenda.txt").write_text(caption, encoding="utf-8")
            except Exception:
                pass
        lst = crossaccount.get_list(list_id) or {}
        self._record_history(
            item.get("url", ""), slot, item.get("meta", {}),
            origin={
                "origin": "cross", "list_id": list_id, "item_id": item_id,
                # de onde veio na outra conta (mostrado no Historico)
                "src_label": item.get("folder", ""),
                "list_name": lst.get("name", ""),
            },
        )
        crossaccount.set_item_field(list_id, item_id, "used", True)
        self._render_cross_list()
        slot_label = str(slot.relative_to(db_folder))
        self._show_toast(f"Enviado para {slot_label}", 3000, OK_BG, OK_FG)

    def _remove_cross_item(self, list_id: str, item_id: str):
        crossaccount.remove_item(list_id, item_id)
        self._populate_cross_combo()
        self._render_cross_list()
        self._show_toast("Removido da lista.", 3000, ERR_BG, ERR_FG)

    def _delete_cross_list(self):
        """Apaga a lista ativa inteira (as imagens da conta de origem ficam intactas)."""
        active = crossaccount.get_active()
        lst = crossaccount.get_list(active) if active else None
        if not lst:
            self._show_toast("Nenhuma lista selecionada.", 3000, ERR_BG, ERR_FG)
            return
        n = len(lst.get("items", []))
        if not self._confirm_dialog(
            "Apagar lista",
            f"A lista '{lst.get('name', '?')}' ({n} publicação(ões)) será apagada.\n"
            "As imagens da conta de origem NÃO são apagadas. Continuar?",
        ):
            return
        crossaccount.delete_list(active)
        self._populate_cross_combo()
        self._render_cross_list(reset_scroll=True)
        self._show_toast("Lista apagada.", 3000, OK_BG, OK_FG)

    def _dup_location_label(self, match, db_folder) -> str:
        """Rotulo 'Dia.../N' de onde a publicacao ja existe no destino."""
        if not match:
            return ""
        folder, _dist = match
        try:
            return str(Path(folder).relative_to(db_folder))
        except ValueError:
            return Path(folder).name

    def _open_folder(self, path: str):
        try:
            p = Path(path)
            if p.is_file():
                p = p.parent
            if p.is_dir():
                os.startfile(str(p))
            else:
                self._show_toast("Pasta não encontrada.", 3000, ERR_BG, ERR_FG)
        except Exception:
            self._show_toast("Não foi possível abrir a pasta.", 3000, ERR_BG, ERR_FG)

    def _refresh_cross_list(self):
        # Com o Recarregar rodando, o mesmo botao vira "Cancelar"
        if getattr(self, "_cross_busy", False):
            ev = getattr(self, "_cross_stop_ev", None)
            if ev is not None:
                ev.set()
                self._cross_log("Cancelamento solicitado — parando…")
            return
        active = crossaccount.get_active()
        if not active:
            return
        db = self.cfg.get("db_folder")
        if not db or not Path(db).is_dir():
            self._show_toast("Selecione a Pasta de Destino primeiro.", 4000, ERR_BG, ERR_FG)
            return
        self._cross_busy = True
        self._cross_stop_ev = threading.Event()
        try:
            self._cross_reload_btn.config(text="✖ Cancelar")
        except (tk.TclError, AttributeError):
            pass
        self._cross_clear_log()          # limpa na thread principal (Tk nao e thread-safe)
        self.cross_progress["value"] = 0
        threading.Thread(target=self._run_cross_refresh, args=(active, Path(db)), daemon=True).start()

    def _run_cross_refresh(self, list_id: str, db_folder: Path):
        try:
            data = crossaccount.load()
            lst = crossaccount.get_list(list_id, data)
            if lst is None:
                return
            name = lst.get("name", "")
            not_used = [it for it in lst.get("items", []) if not it.get("used")]
            # Marcacoes manuais (É/Não é Repetida) nao sao sobrescritas pelo Recarregar
            manual_kept = [it for it in not_used if it.get("manual")]
            avail = [it for it in not_used if not it.get("manual")]
            total = len(avail)
            self._cross_log(f"Recarregando a lista '{name}' — reanalisando {total} item(ns)...")
            if manual_kept:
                self._cross_log(f"  {len(manual_kept)} marcação(ões) manual(is) preservada(s).")
            threshold = self.cfg.get("hash_threshold", 5)
            dest_index = dedup.build_post_index(db_folder)
            changed = 0
            cancelled = False
            for i, it in enumerate(avail, start=1):
                stop_ev = getattr(self, "_cross_stop_ev", None)
                if stop_ev is not None and stop_ev.is_set():
                    cancelled = True
                    break
                self._cross_status(f"Recarregando {i} de {total}...", (i / total * 100) if total else 100)
                if i == 1 or i == total or i % 10 == 0:
                    self._cross_log(f"  reanalisando {i} de {total}")
                hashes = dedup.hashes_from_hex(it.get("hashes", []))
                match = dedup.find_duplicate_post(hashes, dest_index, threshold)
                is_dup = match is not None
                new_loc = self._dup_location_label(match, db_folder) if is_dup else ""
                if bool(it.get("duplicate")) != is_dup or it.get("dup_location", "") != new_loc:
                    it["duplicate"] = is_dup
                    it["dup_location"] = new_loc
                    changed += 1
            # Transacional (estilo React Router): a analise antiga so e substituida
            # quando o Recarregar TERMINA. Cancelou no meio -> descarta o parcial
            # e mantem a analise anterior intacta (nada e salvo).
            if cancelled:
                self._cross_status("Recarregamento cancelado.", 0)
                self._cross_log("Cancelado — nada foi alterado (mantida a análise anterior).")
            else:
                crossaccount.save(data)
                self._cross_status("Recarregado!", 100)
                self._cross_log(f"Concluído — {changed} item(ns) atualizado(s).")
            self.after(0, self._render_cross_list)
        except Exception as exc:
            self._cross_log(f"ERRO: {exc}")
        finally:
            self._cross_busy = False

            def fin():
                try:
                    self._cross_reload_btn.config(text="↻  Recarregar")
                except (tk.TclError, AttributeError):
                    pass
            self.after(0, fin)

    # ------------------------------------------------------------------
    # Toast flutuante (mini balao temporario)
    # ------------------------------------------------------------------

    def _show_toast(self, text: str, ms: int = 3000, bg: str = None, fg: str = None):
        bg = bg or TXT_H
        fg = fg or "#FFFFFF"
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        try:
            toast.attributes("-alpha", 0.97)
        except Exception:
            pass
        frame = tk.Frame(toast, bg=bg, padx=18, pady=10)
        frame.pack()
        tk.Label(frame, text=text, bg=bg, fg=fg, font=FONT_SH).pack()
        toast.update_idletasks()
        w = toast.winfo_reqwidth()
        h = toast.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + self.winfo_height() - h - 70
        toast.geometry(f"+{x}+{y}")
        toast.after(ms, toast.destroy)

    # ------------------------------------------------------------------
    # Aba: Filtro por Link
    # ------------------------------------------------------------------

    def _build_link_tab(self, page):
        PAD = {"padx": 12, "pady": (6, 0)}

        # Card: nova publicacao (agora e a primeira area da tela)
        outer2, card2 = self._make_card(page, "Nova Publicação do Instagram")
        outer2.pack(fill="x", **PAD)

        # Chave seletora: usar agora x adicionar a fila de espera
        # Padrao: 'Adicionar à Fila de Espera' (desde a abertura do app)
        self._var_mode = "queue"
        self._mode_btns = {}
        mode_row = tk.Frame(card2, bg=BORDER, padx=1, pady=1)
        mode_row.pack(fill="x", pady=(0, 8))
        self._mode_row = mode_row
        mode_inner = tk.Frame(mode_row, bg=INNER)
        mode_inner.pack(fill="x")
        for key, label in [("use", "Utilizar agora"),
                           ("queue", "Adicionar à Fila de Espera")]:
            b = tk.Button(
                mode_inner, text=label,
                font=FONT_B, relief="flat", bd=0, cursor="hand2",
                pady=6, command=lambda k=key: self._set_mode(k),
            )
            b.pack(side="left", fill="x", expand=True)
            self._mode_btns[key] = b

        # Destino do salvamento no modo fila: Salvos (geral) ou Salvos + coleção.
        # A linha so aparece no modo 'Adicionar à Fila' (toggle em _set_mode).
        self._q_dest_row = tk.Frame(card2, bg=PANEL)
        tk.Label(self._q_dest_row, text="Salvar em:", font=FONT_B, bg=PANEL,
                 fg=TXT_B).pack(side="left")
        self._q_dest_ids = [None]
        self._q_dest_combo = ttk.Combobox(self._q_dest_row, state="readonly", font=FONT_S)
        self._q_dest_combo.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._q_dest_combo.bind("<<ComboboxSelected>>", self._on_q_dest_selected)

        self._set_mode("queue")

        link_row = tk.Frame(card2, bg=PANEL)
        link_row.pack(fill="x")

        entry_wrap = tk.Frame(link_row, bg=BORDER, padx=1, pady=1)
        entry_wrap.pack(side="left", fill="x", expand=True)
        self.entry_link = tk.Entry(
            entry_wrap, font=FONT_B,
            bg=INNER, fg=TXT_H, insertbackground=TXT_H,
            relief="flat", bd=0,
        )
        self.entry_link.pack(fill="both", expand=True, ipady=5)
        self.entry_link.bind("<KeyRelease>", self._on_link_change)

        self.btn_paste_clear = self._btn(link_row, "Colar", self._paste_or_clear, "secondary")
        self.btn_paste_clear.pack(side="left", padx=(6, 4))
        _start_txt = "Adicionar à Fila" if self._var_mode == "queue" else "Iniciar"
        self.btn_start = self._btn(link_row, _start_txt, self.start_pipeline, "primary")
        self.btn_start.pack(side="left")

        # Card: progresso
        outer3, card3 = self._make_card(page, "Progresso")
        outer3.pack(fill="x", **PAD)
        self.progress = ttk.Progressbar(
            card3, orient="horizontal", mode="determinate",
            maximum=len(STEPS), style="Accent.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(0, 5))
        self.lbl_status = tk.Label(
            card3, text="Aguardando...",
            font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w",
        )
        self.lbl_status.pack(fill="x")

        # Split redimensionavel: LOGs em cima, Historico embaixo.
        # A divisoria "..." (bandeija) e arrastavel para dar mais espaco a um ou outro.
        split = tk.Frame(page, bg=BG)
        split.pack(fill="both", expand=True, pady=(6, 0))
        self._split = split

        # --- LOGs (altura ajustavel via divisoria) ---
        self._logs_holder = tk.Frame(split, bg=BG, height=150)
        self._logs_holder.pack(fill="x", side="top")
        self._logs_holder.pack_propagate(False)
        outer4, card4 = self._make_card(self._logs_holder, "LOGs")
        outer4.pack(fill="both", expand=True, padx=12)
        sb_log = ttk.Scrollbar(card4, orient="vertical")
        self.txt_log = tk.Text(
            card4, height=5, state="disabled", wrap="word",
            yscrollcommand=sb_log.set,
            font=("Consolas", 8),
            bg=INNER, fg=TXT_B, insertbackground=TXT_B,
            relief="flat", bd=0, highlightthickness=0,
            spacing1=1, spacing3=1,
        )
        sb_log.config(command=self.txt_log.yview)
        self.txt_log.pack(side="left", fill="both", expand=True)
        sb_log.pack(side="right", fill="y")

        # --- Divisoria "..." arrastavel (bandeija) ---
        divider = tk.Frame(split, bg=BG, height=18, cursor="sb_v_double_arrow")
        divider.pack(fill="x", side="top")
        divider.pack_propagate(False)
        handle = tk.Frame(divider, bg=INNER, highlightbackground=BORDER, highlightthickness=1)
        handle.place(relx=0.5, rely=0.5, anchor="center", width=46, height=12)
        dots = tk.Label(handle, text="• • •", font=("Segoe UI", 7, "bold"), bg=INNER, fg=TXT_M)
        dots.place(relx=0.5, rely=0.5, anchor="center")
        for w in (divider, handle, dots):
            w.configure(cursor="sb_v_double_arrow")
            w.bind("<Button-1>", self._divider_drag_start)
            w.bind("<B1-Motion>", self._divider_drag)

        # --- Historico compartilhado (timeline do dia) ---
        hist_holder = tk.Frame(split, bg=BG)
        hist_holder.pack(fill="both", expand=True, side="top")
        self._build_history_panel(hist_holder)

    def _build_history_panel(self, parent):
        """Painel de Historico de Envios (compartilhado entre as abas).
        Cada aba tem seu proprio canvas; todos recarregam do mesmo history.json."""
        # Cabecalho:  ◀  HISTÓRICO DE ENVIOS  ▶ ............... Resetar
        hist_hdr = tk.Frame(parent, bg=BG)
        hist_hdr.pack(fill="x", padx=12, pady=(0, 0))
        left = tk.Label(hist_hdr, text="◀", font=("Segoe UI", 11, "bold"),
                        bg=BG, fg=TXT_M, cursor="hand2")
        left.pack(side="left", padx=(0, 5))
        left.bind("<Button-1>", lambda e: self._hist_go(1))     # dia mais antigo
        tk.Label(
            hist_hdr, text="HISTÓRICO DE ENVIOS",
            font=FONT_LBL, bg=BG, fg=TXT_M, anchor="w",
        ).pack(side="left")
        right = tk.Label(hist_hdr, text="▶", font=("Segoe UI", 11, "bold"),
                         bg=BG, fg=TXT_M, cursor="hand2")
        right.pack(side="left", padx=(5, 0))
        right.bind("<Button-1>", lambda e: self._hist_go(-1))   # dia mais novo
        reset_btn = self._btn(hist_hdr, "Resetar", self._reset_history, "danger_sm")
        reset_btn.pack(side="right")

        # Rotulo do dia que estamos vendo (centralizado)
        nav = tk.Frame(parent, bg=BG)
        nav.pack(fill="x", padx=12, pady=(1, 3))
        day_lbl = tk.Label(nav, text="Lista de Publicações do Dia", font=FONT_S,
                           bg=BG, fg=TXT_B, anchor="center")
        day_lbl.pack(fill="x", expand=True)
        self._hist_headers.append({"day": day_lbl, "left": left, "right": right,
                                   "reset": reset_btn})

        hist_outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        hist_outer.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        hist_card = tk.Frame(hist_outer, bg=PANEL)
        hist_card.pack(fill="both", expand=True)

        canvas = tk.Canvas(hist_card, borderwidth=0, highlightthickness=0, height=120, bg=PANEL)
        sb = ttk.Scrollbar(hist_card, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        inner = tk.Frame(canvas, bg=PANEL)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.bind("<Configure>", lambda e, c=canvas, i=inner_id: c.itemconfigure(i, width=e.width))
        canvas.bind("<Enter>", lambda e, c=canvas: c.bind_all(
            "<MouseWheel>", lambda ev, cc=c: cc.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
        canvas.bind("<Leave>", lambda e, c=canvas: c.unbind_all("<MouseWheel>"))
        self._hist_inners.append(inner)
        self._start_day_watch()

    # ------------------------------------------------------------------
    # Aba: Filtro Entre Contas
    # ------------------------------------------------------------------

    def _build_cross_tab(self, page):
        PAD = {"padx": 12, "pady": (6, 0)}

        # Card: pasta da conta de origem + nome da lista
        outer, card = self._make_card(page, "Pasta de Publicações da Conta de Origem")
        outer.pack(fill="x", **PAD)
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x")
        self.lbl_src_folder = tk.Label(
            row, text="(nenhuma pasta selecionada)",
            font=FONT_B, bg=PANEL, fg=TXT_M, anchor="w",
        )
        self.lbl_src_folder.pack(side="left", fill="x", expand=True)
        self._btn(row, "Selecionar...", self.choose_src_folder, "secondary").pack(
            side="right", padx=(10, 0)
        )

        name_row = tk.Frame(card, bg=PANEL)
        name_row.pack(fill="x", pady=(10, 0))
        tk.Label(name_row, text="Nome da lista:", font=FONT_B, bg=PANEL, fg=TXT_B).pack(side="left")
        name_wrap = tk.Frame(name_row, bg=BORDER, padx=1, pady=1)
        name_wrap.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.entry_list_name = tk.Entry(
            name_wrap, font=FONT_B, bg=INNER, fg=TXT_H, insertbackground=TXT_H,
            relief="flat", bd=0,
        )
        self.entry_list_name.pack(fill="both", expand=True, ipady=4)
        self.btn_cross_start = self._btn(name_row, "Analisar Conta", self.start_cross_import, "primary")
        self.btn_cross_start.pack(side="right")

        # Card: progresso
        outer3, card3 = self._make_card(page, "Progresso")
        outer3.pack(fill="x", **PAD)
        self.cross_progress = ttk.Progressbar(
            card3, orient="horizontal", mode="determinate",
            maximum=100, style="Accent.Horizontal.TProgressbar",
        )
        self.cross_progress.pack(fill="x", pady=(0, 5))
        self.cross_lbl_status = tk.Label(
            card3, text="Aguardando...", font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w",
        )
        self.cross_lbl_status.pack(fill="x")

        # Card: LOGs (altura fixa)
        logs_holder = tk.Frame(page, bg=BG, height=140)
        logs_holder.pack(fill="x", pady=(6, 0))
        logs_holder.pack_propagate(False)
        outer4, card4 = self._make_card(logs_holder, "LOGs")
        outer4.pack(fill="both", expand=True, padx=12)
        sb_log = ttk.Scrollbar(card4, orient="vertical")
        self.cross_txt_log = tk.Text(
            card4, height=5, state="disabled", wrap="word", yscrollcommand=sb_log.set,
            font=("Consolas", 8), bg=INNER, fg=TXT_B, insertbackground=TXT_B,
            relief="flat", bd=0, highlightthickness=0, spacing1=1, spacing3=1,
        )
        sb_log.config(command=self.cross_txt_log.yview)
        self.cross_txt_log.pack(side="left", fill="both", expand=True)
        sb_log.pack(side="right", fill="y")

        # Historico compartilhado
        hist_holder = tk.Frame(page, bg=BG)
        hist_holder.pack(fill="both", expand=True, side="top")
        self._build_history_panel(hist_holder)

    # ------------------------------------------------------------------
    # Aba: Feed Especial ("Instagram Saudavel") — Fase 1
    # ------------------------------------------------------------------

    def _build_feed_tab(self, page):
        PAD = {"padx": 12, "pady": (6, 0)}
        feed = feedinbox.get_or_create_default_feed()
        cfg = {**feedinbox.DEFAULT_CONFIG, **(feed.get("config") or {})}
        self._feed_id = feed["id"]

        outer, card = self._make_card(page, "Feed Especial — Conta-Isca")
        outer.pack(fill="x", **PAD)

        vcmd = (self.register(lambda v: v == "" or v.isdigit()), "%P")

        def cfg_entry(parent, var, width=8):
            wrap = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
            tk.Entry(wrap, textvariable=var, width=width, font=FONT_B, justify="center",
                     bg=INNER, fg=TXT_H, insertbackground=TXT_H, relief="flat", bd=0,
                     validate="key", validatecommand=vcmd).pack(ipady=3)
            return wrap

        self._fv_likes_min = tk.StringVar(value=str(cfg.get("likes_min", 20000)))
        self._fv_likes_max = tk.StringVar(value=str(cfg.get("likes_max", 1000000)))
        self._fv_comm_min = tk.StringVar(value=str(cfg.get("comments_min", 200)))
        self._fv_minutes = tk.StringVar(value=str(cfg.get("scroll_minutes", 10)))
        self._fv_only_car = tk.BooleanVar(value=bool(cfg.get("only_carousels", True)))

        r1 = tk.Frame(card, bg=PANEL)
        r1.pack(fill="x")
        tk.Label(r1, text="Curtidas de", font=FONT_B, bg=PANEL, fg=TXT_B).pack(side="left")
        cfg_entry(r1, self._fv_likes_min).pack(side="left", padx=4)
        tk.Label(r1, text="a", font=FONT_B, bg=PANEL, fg=TXT_B).pack(side="left")
        cfg_entry(r1, self._fv_likes_max).pack(side="left", padx=4)
        tk.Label(r1, text="   Comentários ≥", font=FONT_B, bg=PANEL, fg=TXT_B).pack(side="left")
        cfg_entry(r1, self._fv_comm_min, width=6).pack(side="left", padx=4)

        r2 = tk.Frame(card, bg=PANEL)
        r2.pack(fill="x", pady=(8, 0))
        tk.Checkbutton(
            r2, text="Somente carrosséis", variable=self._fv_only_car,
            font=FONT_B, bg=PANEL, fg=TXT_B, activebackground=PANEL,
            activeforeground=TXT_H, selectcolor=PANEL, cursor="hand2",
        ).pack(side="left")
        tk.Label(r2, text="   Coleta de", font=FONT_B, bg=PANEL, fg=TXT_B).pack(side="left")
        cfg_entry(r2, self._fv_minutes, width=4).pack(side="left", padx=4)
        tk.Label(r2, text="min", font=FONT_B, bg=PANEL, fg=TXT_B).pack(side="left")
        self._btn(r2, "Salvar Config", lambda: self._save_feed_config(), "secondary_sm").pack(side="right")

        r3 = tk.Frame(card, bg=PANEL)
        r3.pack(fill="x", pady=(10, 0))
        self._feed_collect_btn = self._btn(r3, "▶ Coletar agora", self._start_feed_collect, "primary")
        self._feed_collect_btn.pack(side="left")
        self._btn(r3, "🗑 Limpar feed", self._clear_feed_flow, "danger_sm").pack(side="left", padx=(8, 0))
        self._feed_status_lbl = tk.Label(r3, text="", font=FONT_S, bg=PANEL, fg=TXT_M, anchor="e")
        self._feed_status_lbl.pack(side="right", fill="x", expand=True)

        # LOGs da coleta (compactos)
        logs_holder = tk.Frame(page, bg=BG, height=92)
        logs_holder.pack(fill="x", pady=(6, 0), padx=12)
        logs_holder.pack_propagate(False)
        louter, lcard = self._make_card(logs_holder, "LOGs da Coleta")
        louter.pack(fill="both", expand=True)
        lsb = ttk.Scrollbar(lcard, orient="vertical")
        self._feed_txt_log = tk.Text(
            lcard, height=3, state="disabled", wrap="word", yscrollcommand=lsb.set,
            font=("Consolas", 8), bg=INNER, fg=TXT_B, insertbackground=TXT_B,
            relief="flat", bd=0, highlightthickness=0, spacing1=1, spacing3=1,
        )
        lsb.config(command=self._feed_txt_log.yview)
        self._feed_txt_log.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")

        # O feed em si (rolagem estilo Instagram, virtualizado)
        f_holder = tk.Frame(page, bg=BG)
        f_holder.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        f_outer = tk.Frame(f_holder, bg=BORDER, padx=1, pady=1)
        f_outer.pack(fill="both", expand=True)
        f_card = tk.Frame(f_outer, bg=PANEL)
        f_card.pack(fill="both", expand=True)
        self._feed_canvas = tk.Canvas(f_card, borderwidth=0, highlightthickness=0, bg=PANEL)
        fsb = ttk.Scrollbar(f_card, orient="vertical", command=self._feed_yview)
        self._feed_canvas.configure(yscrollcommand=fsb.set)
        self._feed_inner = tk.Frame(self._feed_canvas, bg=PANEL)
        self._feed_inner_id = self._feed_canvas.create_window((0, 0), window=self._feed_inner, anchor="nw")
        self._feed_canvas.pack(side="left", fill="both", expand=True)
        fsb.pack(side="right", fill="y")
        self._feed_inner.bind(
            "<Configure>",
            lambda e: self._feed_canvas.configure(scrollregion=self._feed_canvas.bbox("all")),
        )
        self._feed_canvas.bind("<Configure>", self._on_feed_canvas_configure)
        self._feed_canvas.bind(
            "<Enter>", lambda e: self._feed_canvas.bind_all("<MouseWheel>", self._on_feed_scroll))
        self._feed_canvas.bind(
            "<Leave>", lambda e: self._feed_canvas.unbind_all("<MouseWheel>"))
        self._feed_rows = {}
        self._feed_items = []

    def _feed_log(self, msg: str):
        def apply():
            try:
                self._feed_txt_log.config(state="normal")
                self._feed_txt_log.insert("end", msg + "\n")
                self._feed_txt_log.see("end")
                self._feed_txt_log.config(state="disabled")
            except tk.TclError:
                pass
        self.after(0, apply)

    def _save_feed_config(self, silent: bool = False):
        def num(var, dft):
            try:
                return int(var.get() or dft)
            except (ValueError, tk.TclError):
                return dft
        feedinbox.update_config(self._feed_id, {
            "likes_min": num(self._fv_likes_min, 20000),
            "likes_max": num(self._fv_likes_max, 1000000),
            "comments_min": num(self._fv_comm_min, 200),
            "scroll_minutes": max(1, num(self._fv_minutes, 10)),
            "only_carousels": bool(self._fv_only_car.get()),
        })
        if not silent:
            self._show_toast("Configurações do Feed salvas.", 3000, OK_BG, OK_FG)

    def _start_feed_collect(self):
        """1º clique inicia a coleta; com a coleta rodando, o clique pede parada."""
        if getattr(self, "_feed_collect_busy", False):
            ev = getattr(self, "_feed_stop_ev", None)
            if ev is not None:
                ev.set()
                self._feed_log("Parada solicitada — encerrando o ciclo atual…")
            return
        self._save_feed_config(silent=True)   # aplica o que estiver nos campos
        self._feed_collect_busy = True
        self._feed_stop_ev = threading.Event()
        self._feed_collect_btn.config(text="■ Parar coleta")
        # Cronometro: inicio + decorrido + restante, atualizado a cada segundo
        try:
            self._feed_run_minutes = max(1, int(self._fv_minutes.get() or 10))
        except (ValueError, tk.TclError):
            self._feed_run_minutes = 10
        self._feed_run_started = datetime.now()
        self._feed_timer_tick()
        threading.Thread(target=self._run_feed_collect, daemon=True).start()

    def _feed_timer_tick(self):
        if not getattr(self, "_feed_collect_busy", False):
            self._update_feed_status()   # volta ao status normal do feed
            return
        start = getattr(self, "_feed_run_started", None)
        if start is None:
            return
        elapsed = (datetime.now() - start).total_seconds()
        remain = max(0.0, getattr(self, "_feed_run_minutes", 10) * 60 - elapsed)

        def fmt(s):
            return f"{int(s // 60):02d}:{int(s % 60):02d}"

        try:
            self._feed_status_lbl.config(
                text=f"⏱ Coletando — início {start.strftime('%H:%M:%S')} · "
                     f"decorrido {fmt(elapsed)} · restam {fmt(remain)}")
        except tk.TclError:
            pass
        self.after(1000, self._feed_timer_tick)

    def _run_feed_collect(self):
        try:
            feedbot.collect(self._feed_id, progress_cb=self._feed_log,
                            login_wait_cb=self._login_wait_cb,
                            should_stop=self._feed_stop_ev)
        except Exception as exc:
            self._feed_log(f"ERRO na coleta: {exc}")
        finally:
            self._feed_collect_busy = False

            def fin():
                try:
                    self._feed_collect_btn.config(text="▶ Coletar agora")
                except tk.TclError:
                    pass
                self._reload_feed_view()
            self.after(0, fin)

    def _clear_feed_flow(self):
        c = feedinbox.counts(self._feed_id)
        total = sum(c.values())
        if not total:
            self._show_toast("O feed já está vazio.", 3000, ERR_BG, ERR_FG)
            return
        if not self._confirm_dialog(
            "Limpar feed",
            f"As {total} publicação(ões) do feed (e suas capas) serão removidas.\n"
            "O que já foi salvo nos Salvos/Coleções NÃO é afetado. Continuar?",
        ):
            return
        feedinbox.clear_feed(self._feed_id)
        self._reload_feed_view()
        self._show_toast("Feed limpo.", 3000, OK_BG, OK_FG)

    def _update_feed_status(self):
        c = feedinbox.counts(self._feed_id)
        feed = feedinbox.get_feed(self._feed_id)
        last = (feed or {}).get("last_collect", "") or "nunca"
        try:
            self._feed_status_lbl.config(
                text=f"{c.get('new', 0)} no feed · {c.get('saved', 0)} salvas · "
                     f"{c.get('discarded', 0)} descartadas · última coleta: {last}")
        except tk.TclError:
            pass

    def _reload_feed_view(self, keep_scroll: bool = False):
        if not hasattr(self, "_feed_inner"):
            return
        frac = self._feed_canvas.yview()[0] if keep_scroll else 0.0
        for w in self._feed_inner.winfo_children():
            w.destroy()
        self._feed_rows = {}
        items = feedinbox.items_by_status(self._feed_id, "new")
        items.reverse()   # mais recentes primeiro, como no Instagram
        self._feed_items = items
        self._update_feed_status()
        if not items:
            self._feed_inner.configure(height=140)
            tk.Label(
                self._feed_inner,
                text="Feed vazio.\n\nClique em '▶ Coletar agora' para o robô rolar a\n"
                     "conta-isca e trazer publicações do seu gosto.",
                fg=TXT_M, font=FONT_B, bg=PANEL, justify="center",
            ).place(x=16, y=24)
            return
        self._feed_inner.configure(height=len(items) * FEED_ROW_H + 4)
        self._feed_canvas.yview_moveto(frac)
        self._feed_virtual_update()

    def _feed_virtual_update(self):
        """Igual a lista Entre Contas: so cria as publicacoes visiveis (+ margem)."""
        if not getattr(self, "_feed_items", None) or not hasattr(self, "_feed_rows"):
            return
        canvas = self._feed_canvas
        try:
            top = max(0.0, canvas.canvasy(0))
        except Exception:
            top = 0.0
        vh = canvas.winfo_height() or 1
        n = len(self._feed_items)
        i0 = max(0, int(top // FEED_ROW_H) - FEED_OVERSCAN)
        i1 = min(n - 1, int((top + vh) // FEED_ROW_H) + FEED_OVERSCAN)
        want = set(range(i0, i1 + 1))
        have = set(self._feed_rows.keys())
        for i in have - want:
            try:
                self._feed_rows[i].destroy()
            except Exception:
                pass
            del self._feed_rows[i]
        for i in want - have:
            row = self._build_feed_row(self._feed_items[i])
            row.place(x=4, y=i * FEED_ROW_H, relwidth=1, width=-8)
            self._feed_rows[i] = row

    def _on_feed_scroll(self, event):
        self._feed_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._feed_virtual_update()

    def _feed_yview(self, *args):
        self._feed_canvas.yview(*args)
        self._feed_virtual_update()

    def _on_feed_canvas_configure(self, event):
        self._feed_canvas.itemconfigure(self._feed_inner_id, width=event.width)
        self._feed_virtual_update()

    def _build_feed_row(self, item: dict):
        row_outer = tk.Frame(self._feed_inner, bg=BORDER, padx=1, pady=1)
        row = tk.Frame(row_outer, bg=PANEL, padx=10, pady=8)
        row.pack(fill="both", expand=True)

        hdr = tk.Frame(row, bg=PANEL)
        hdr.pack(fill="x")
        tk.Label(hdr, text=item.get("shortcode", "?"), font=FONT_SH,
                 bg=PANEL, fg=TXT_H).pack(side="left")
        badge = " · carrossel" if item.get("carousel") else ""
        tk.Label(hdr, text=f"❤ {item.get('likes', 'N/D')} · 💬 {item.get('comments', 'N/D')}{badge}",
                 font=FONT_S, bg=PANEL, fg=TXT_M).pack(side="right")

        img_frame = tk.Frame(row, bg=INNER, width=FEED_IMG, height=FEED_IMG)
        img_frame.pack(pady=(6, 0))
        img_frame.pack_propagate(False)
        tp = item.get("thumb", "")
        shown = False
        if tp and Path(tp).exists():
            try:
                im = Image.open(tp).convert("RGB")
                w, h = im.size
                m = min(w, h)
                im = im.crop(((w - m) // 2, (h - m) // 2, (w - m) // 2 + m, (h - m) // 2 + m))
                im = im.resize((FEED_IMG, FEED_IMG), Image.LANCZOS)
                ph = ImageTk.PhotoImage(im)
                row_outer._photo = ph
                tk.Label(img_frame, image=ph, bg=INNER).pack()
                shown = True
            except Exception:
                pass
        if not shown:
            tk.Label(img_frame, text="[capa indisponível]", fg=TXT_M,
                     font=FONT_B, bg=INNER).pack(expand=True)

        cap = (item.get("caption") or "").strip()
        if cap:
            tk.Label(row, text=cap[:110] + ("…" if len(cap) > 110 else ""),
                     font=FONT_S, bg=PANEL, fg=TXT_B, anchor="w",
                     wraplength=FEED_IMG).pack(fill="x", pady=(6, 0))

        btns = tk.Frame(row, bg=PANEL)
        btns.pack(fill="x", pady=(8, 0))
        self._btn(btns, "💾 Salvar em…",
                  lambda it=item: self._feed_save_item(it), "green_sm").pack(side="left")
        self._btn(btns, "🔗", lambda u=item.get("url", ""): webbrowser.open(u),
                  "secondary_sm").pack(side="left", padx=(6, 0))
        self._btn(btns, "✕ Descartar",
                  lambda it=item: self._feed_discard_item(it), "danger_sm").pack(side="right")
        return row_outer

    def _ask_feed_dest(self):
        """Modal: destino do salvamento (Salvos geral ou Salvos + colecao).
        Retorna (confirmou, col_id_ou_None)."""
        cols = waitqueue.load_collections()
        ids = [None] + [c.get("id") for c in cols]
        result = [(False, None)]
        dlg = tk.Toplevel(self)
        dlg.title("Salvar publicação")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.configure(bg=PANEL)
        tk.Label(dlg, text="Salvar esta publicação em:", bg=PANEL, fg=TXT_B,
                 font=FONT_B).pack(padx=26, pady=(18, 8))
        combo = ttk.Combobox(dlg, state="readonly", font=FONT_B,
                             values=["Salvos (geral)"] + [f"Salvos + {c.get('name', '?')}" for c in cols])
        combo.current(0)
        combo.pack(fill="x", padx=26, ipady=3)
        btn_row = tk.Frame(dlg, bg=PANEL)
        btn_row.pack(pady=(16, 18))

        def ok():
            idx = combo.current()
            result[0] = (True, ids[idx] if 0 <= idx < len(ids) else None)
            dlg.destroy()

        self._btn(btn_row, "CANCELAR", dlg.destroy, "secondary").pack(side="left", padx=(0, 10))
        self._btn(btn_row, "SALVAR", ok, "primary").pack(side="left")
        self.update_idletasks()
        dlg.update_idletasks()
        w, h = 380, 170
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.wait_window()
        return result[0]

    def _feed_save_item(self, item: dict):
        """Salvar do feed = pipeline existente em modo fila (baixa via SnapInsta,
        checa repetidas) + colecao de destino. No sucesso o item sai do feed."""
        if getattr(self, "_metrics_busy", False) or str(self.btn_start["state"]) == "disabled":
            self._show_toast("Aguarde o processo atual terminar.", 4000, ERR_BG, ERR_FG)
            return
        if getattr(self, "_feed_collect_busy", False):
            self._show_toast("Aguarde (ou pare) a coleta para salvar.", 4000, ERR_BG, ERR_FG)
            return
        db = self.cfg.get("db_folder")
        if not db or not Path(db).is_dir():
            self._show_toast("Selecione a Pasta de Destino primeiro.", 4000, ERR_BG, ERR_FG)
            return
        ok, dest = self._ask_feed_dest()
        if not ok:
            return
        self.btn_start.config(state="disabled")
        self.btn_paste_clear.config(state="disabled")
        self.progress["value"] = 0
        self.lbl_status.config(text=STEPS[0])
        self.clear_log()
        self._feed_log(f"Salvando {item.get('shortcode', '?')} nos Salvos… "
                       "(progresso na aba Filtro por Link)")
        threading.Thread(
            target=self._run_pipeline,
            args=(item.get("url", ""), Path(db), "queue", dest),
            kwargs={"feed_mark": (self._feed_id, item.get("id", ""))},
            daemon=True,
        ).start()

    def _send_entry_to_collection_folder(self, entry: dict):
        """Materializa a publicacao na PASTA da colecao aberta: cria (se preciso)
        '<Pasta de Destino>\\<Nome da Colecao> <data de criacao>' e salva as imagens
        na proxima subpasta numerada — util p/ produtos/estrategias em sequencia."""
        col = next((c for c in waitqueue.load_collections()
                    if c.get("id") == getattr(self, "_q_view_col", None)), None)
        if col is None:
            return
        db = self.cfg.get("db_folder")
        if not db or not Path(db).is_dir():
            self._show_toast("Selecione a Pasta de Destino primeiro.", 4000, ERR_BG, ERR_FG)
            return
        images = waitqueue.entry_images(entry)
        if not images:
            self._show_toast("Imagens não encontradas.", 4000, ERR_BG, ERR_FG)
            return
        created = (col.get("created", "") or "").split(" ")[0].replace("/", "-")
        folder_name = f"{col.get('name', 'Coleção')} {created}".strip()
        if not self._confirm_dialog(
            "Enviar para a pasta da coleção",
            f"Salvar '{entry.get('shortcode', '?')}' na pasta \"{folder_name}\" "
            "(próxima subpasta numerada) e removê-la dos Salvos?",
        ):
            return
        folder = Path(db) / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        nums = [int(d.name) for d in folder.iterdir() if d.is_dir() and d.name.isdigit()]
        slot = folder / str(max(nums) + 1 if nums else 1)
        slot.mkdir()
        organizer.save_media_to_slot(slot, images)
        waitqueue.remove_from_queue(entry.get("id", ""))
        self._reload_queue_panel()
        self._show_toast(f"Enviada para {folder_name}\\{slot.name}", 3500, OK_BG, OK_FG)

    def _feed_discard_item(self, item: dict):
        """Descarta do feed — vira exemplo NEGATIVO do filtro de gosto (Fase 2)."""
        feedinbox.set_item_status(self._feed_id, item.get("id", ""), "discarded")
        self._reload_feed_view(keep_scroll=True)
        self._show_toast("Descartada — o filtro aprende com isso.", 2500, OK_BG, OK_FG)

    # ------------------------------------------------------------------
    # Aba configuracoes
    # ------------------------------------------------------------------

    def _build_settings_tab(self, page):
        PAD = {"padx": 12, "pady": (10, 0)}

        # A aba inteira rola (os cards passaram da altura da janela): canvas +
        # scrollbar + rodinha do mouse, no mesmo padrao do Historico/Salvos
        canvas = tk.Canvas(page, borderwidth=0, highlightthickness=0, bg=BG)
        sb = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        inner = tk.Frame(canvas, bg=BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        inner.bind(
            "<Configure>",
            lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda e, c=canvas, i=inner_id: c.itemconfigure(i, width=e.width),
        )
        canvas.bind("<Enter>", lambda e, c=canvas: c.bind_all(
            "<MouseWheel>",
            lambda ev, cc=c: cc.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
        canvas.bind("<Leave>", lambda e, c=canvas: c.unbind_all("<MouseWheel>"))
        page = inner   # daqui pra baixo, todos os cards entram na area rolavel

        # Card: pasta de destino (onde as pastas dos dias sao criadas / base de comparacao)
        outer0, card0 = self._make_card(page, "Pasta de Destino")
        outer0.pack(fill="x", **PAD)
        tk.Label(
            card0,
            text="Pasta onde ficam seus envios (base de comparação) e onde as pastas dos próximos dias são criadas.",
            font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w", wraplength=520, justify="left",
        ).pack(fill="x", pady=(0, 8))
        row0 = tk.Frame(card0, bg=PANEL)
        row0.pack(fill="x")
        self.lbl_db_folder = tk.Label(
            row0, text="(nenhuma pasta selecionada)",
            font=FONT_B, bg=PANEL, fg=TXT_M, anchor="w",
        )
        self.lbl_db_folder.pack(side="left", fill="x", expand=True)
        self._btn(row0, "Selecionar...", self.choose_db_folder, "secondary").pack(
            side="right", padx=(10, 0)
        )

        # Card: nomenclatura
        outer, card = self._make_card(page, "Nomenclatura das Pastas")
        outer.pack(fill="x", **PAD)

        tk.Label(
            card,
            text="Defina quais elementos aparecem no nome da pasta de envio diária.",
            font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w", wraplength=500,
        ).pack(fill="x", pady=(0, 10))

        tk.Checkbutton(
            card,
            text="Incluir contador de dias  (Dia1, Dia2, Dia24...)",
            variable=self._var_counter,
            font=FONT_B, bg=PANEL, fg=TXT_B,
            activebackground=PANEL, activeforeground=TXT_H,
            selectcolor=PANEL, cursor="hand2",
        ).pack(anchor="w")

        initial_row = tk.Frame(card, bg=PANEL)
        initial_row.pack(fill="x", pady=(8, 0))

        tk.Checkbutton(
            initial_row,
            text="Incluir inicial da pessoa",
            variable=self._var_initial,
            font=FONT_B, bg=PANEL, fg=TXT_B,
            activebackground=PANEL, activeforeground=TXT_H,
            selectcolor=PANEL, cursor="hand2",
        ).pack(side="left")

        tk.Label(initial_row, text="   Inicial:", font=FONT_B, bg=PANEL, fg=TXT_B).pack(
            side="left"
        )

        vcmd_letter = (
            self.register(lambda v: len(v) <= 1 and (v == "" or v.isalpha())), "%P"
        )
        letter_wrap = tk.Frame(initial_row, bg=BORDER, padx=1, pady=1)
        letter_wrap.pack(side="left", padx=(4, 0))
        self.entry_letter = tk.Entry(
            letter_wrap, textvariable=self._var_letter,
            font=FONT_SH, width=3, justify="center",
            bg=INNER, fg=TXT_H, insertbackground=TXT_H,
            relief="flat", bd=0,
            validate="key", validatecommand=vcmd_letter,
        )
        self.entry_letter.pack(ipady=4)
        if not self._var_initial.get():
            self.entry_letter.config(state="disabled")

        # Preview
        preview_wrap = tk.Frame(card, bg=INNER, padx=12, pady=10)
        preview_wrap.pack(fill="x", pady=(14, 0))
        tk.Label(
            preview_wrap, text="Exemplo de pasta que será criada:",
            font=FONT_M, bg=INNER, fg=TXT_M, anchor="w",
        ).pack(fill="x")
        self._lbl_preview = tk.Label(
            preview_wrap, text="",
            font=("Consolas", 11, "bold"), bg=INNER, fg=TXT_H, anchor="w",
        )
        self._lbl_preview.pack(fill="x")

        # Card: parametros de envio
        outer2, card2 = self._make_card(page, "Parâmetros de Envio")
        outer2.pack(fill="x", **PAD)

        slots_row = tk.Frame(card2, bg=PANEL)
        slots_row.pack(fill="x")
        tk.Label(
            slots_row, text="Publicações por dia:",
            font=FONT_B, bg=PANEL, fg=TXT_B,
        ).pack(side="left")
        vcmd_int = (
            self.register(lambda v: v == "" or (v.isdigit() and 1 <= int(v) <= 99)), "%P"
        )
        slots_wrap = tk.Frame(slots_row, bg=BORDER, padx=1, pady=1)
        slots_wrap.pack(side="left", padx=(8, 0))
        tk.Entry(
            slots_wrap, textvariable=self._var_slots,
            width=4, font=FONT_B, justify="center",
            bg=INNER, fg=TXT_H, relief="flat", bd=0,
            validate="key", validatecommand=vcmd_int,
        ).pack(ipady=4)

        # Card: deteccao de duplicatas
        outer3, card3 = self._make_card(page, "Detecção de Duplicatas")
        outer3.pack(fill="x", **PAD)

        thresh_row = tk.Frame(card3, bg=PANEL)
        thresh_row.pack(fill="x")
        tk.Label(
            thresh_row, text="Limiar de similaridade:",
            font=FONT_B, bg=PANEL, fg=TXT_B,
        ).pack(side="left")
        vcmd_thr = (
            self.register(lambda v: v == "" or (v.isdigit() and int(v) <= 30)), "%P"
        )
        thresh_wrap = tk.Frame(thresh_row, bg=BORDER, padx=1, pady=1)
        thresh_wrap.pack(side="left", padx=(8, 0))
        tk.Entry(
            thresh_wrap, textvariable=self._var_thresh,
            width=4, font=FONT_B, justify="center",
            bg=INNER, fg=TXT_H, relief="flat", bd=0,
            validate="key", validatecommand=vcmd_thr,
        ).pack(ipady=4)
        tk.Label(
            thresh_row,
            text="   (0 = idêntico · quanto maior, mais tolerante)",
            font=FONT_M, bg=PANEL, fg=TXT_M,
        ).pack(side="left")

        purge_row = tk.Frame(card3, bg=PANEL)
        purge_row.pack(fill="x", pady=(12, 0))
        tk.Label(
            purge_row,
            text="Trocou muitos Cards Finais? Apague os caches: os hashes de todas as "
                 "pastas da Pasta de Destino serão recalculados das imagens atuais.",
            font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w", wraplength=350, justify="left",
        ).pack(side="left", fill="x", expand=True)
        self.btn_purge_hashes = self._btn(
            purge_row, "Apagar caches de hash", self._purge_hash_caches, "secondary"
        )
        self.btn_purge_hashes.pack(side="right", padx=(10, 0))

        # Card: logins do Instagram (uma sessao de navegador por funcao)
        outer_lg, card_lg = self._make_card(page, "Logins do Instagram (por função)")
        outer_lg.pack(fill="x", **PAD)
        tk.Label(
            card_lg,
            text="Cada função usa um navegador com sessão própria. Abra o navegador da "
                 "função para logar/deslogar quando quiser — a sessão fica salva e é usada "
                 "automaticamente nas próximas vezes.",
            font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w", wraplength=520, justify="left",
        ).pack(fill="x", pady=(0, 8))
        self._login_btns = {}
        self._login_status_lbls = {}
        for kind, title, desc in [
            ("analysis", "Análise por Link (métricas)",
             "Conta usada para buscar curtidas/comentários das publicações analisadas"),
            ("feed", "Feed Especial (conta-isca)",
             "Conta cujo feed o robô rola para captar publicações do seu gosto"),
            ("publish", "Programar Publicações",
             "Inativo — reservado para a futura função de agendar posts"),
        ]:
            r = tk.Frame(card_lg, bg=PANEL)
            r.pack(fill="x", pady=(4, 0))
            box = tk.Frame(r, bg=PANEL)
            box.pack(side="left", fill="x", expand=True)
            tk.Label(box, text=title, font=FONT_B, bg=PANEL, fg=TXT_H,
                     anchor="w").pack(fill="x")
            st = tk.Label(box, text=desc, font=FONT_S, bg=PANEL, fg=TXT_M,
                          anchor="w", wraplength=380, justify="left")
            st.pack(fill="x")
            self._login_status_lbls[kind] = st
            b = self._btn(r, "Abrir navegador",
                          lambda k=kind: self._open_login_browser(k), "secondary")
            b.pack(side="right", padx=(10, 0))
            self._login_btns[kind] = b
        self._login_btns["publish"].config(state="disabled", text="Em breve")

        # Card: aparencia (tema claro / escuro)
        outer4, card4 = self._make_card(page, "Aparência")
        outer4.pack(fill="x", **PAD)
        tk.Label(
            card4,
            text="Escolha o tema visual do aplicativo (aplica na hora).",
            font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w",
        ).pack(fill="x", pady=(0, 8))
        theme_row = tk.Frame(card4, bg=BORDER, padx=1, pady=1)
        theme_row.pack(fill="x")
        theme_inner = tk.Frame(theme_row, bg=INNER)
        theme_inner.pack(fill="x")
        self._theme_btns = {}
        cur_theme = self._var_theme.get()
        for key, label in [("light", "☀  Claro"), ("dark", "☾  Escuro")]:
            active = (key == cur_theme)
            b = tk.Button(
                theme_inner, text=label,
                font=FONT_B, relief="flat", bd=0, cursor="hand2", pady=6,
                bg=ACCENT if active else INNER,
                fg="#FFFFFF" if active else TXT_M,
                activebackground=ACCENT if active else INNER,
                activeforeground="#FFFFFF" if active else TXT_B,
                command=lambda k=key: self._set_theme(k),
            )
            b.pack(side="left", fill="x", expand=True)
            self._theme_btns[key] = b

        # Botao salvar
        save_row = tk.Frame(page, bg=BG)
        save_row.pack(fill="x", padx=12, pady=(16, 12))
        self._btn(save_row, "Salvar Configurações", self._save_settings, "primary").pack(
            side="right"
        )

    # ------------------------------------------------------------------
    # Fabrica de widgets utilitarios
    # ------------------------------------------------------------------

    def _make_card(self, parent, title: str = None):
        """Retorna (outer_frame, content_frame). Empacote o outer na tela."""
        outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        content = tk.Frame(outer, bg=PANEL, padx=14, pady=11)
        content.pack(fill="both", expand=True)
        if title:
            tk.Label(
                content, text=title.upper(),
                font=FONT_LBL, bg=PANEL, fg=TXT_M, anchor="w",
            ).pack(fill="x", pady=(0, 8))
        return outer, content

    def _btn(self, parent, text: str, command, style: str = "primary") -> tk.Button:
        styles = {
            "primary": {
                "bg": BPF, "fg": BPT,
                "activebackground": BPA, "activeforeground": BPT,
                "font": FONT_SH, "padx": 14, "pady": 7,
            },
            "secondary": {
                "bg": BSF, "fg": BST,
                "activebackground": BORDER, "activeforeground": BST,
                "font": FONT_B, "padx": 10, "pady": 6,
            },
            "danger": {
                "bg": BDF, "fg": BDT,
                "activebackground": "#B91C1C", "activeforeground": BDT,
                "font": FONT_SH, "padx": 14, "pady": 7,
            },
            "danger_sm": {
                "bg": BDF, "fg": BDT,
                "activebackground": "#B91C1C", "activeforeground": BDT,
                "font": FONT_M, "padx": 8, "pady": 3,
            },
            "green_sm": {
                "bg": BGF, "fg": BGT,
                "activebackground": "#15803D", "activeforeground": BGT,
                "font": FONT_M, "padx": 8, "pady": 4,
            },
            "secondary_sm": {
                "bg": BSF, "fg": BST,
                "activebackground": BORDER, "activeforeground": BST,
                "font": FONT_M, "padx": 8, "pady": 4,
            },
        }
        s = styles.get(style, styles["primary"])
        return tk.Button(
            parent, text=text, command=command,
            relief="flat", bd=0, cursor="hand2",
            **s,
        )

    # ------------------------------------------------------------------
    # Logica da aba de configuracoes
    # ------------------------------------------------------------------

    def _update_preview(self, *_):
        if not hasattr(self, "_lbl_preview") or self._lbl_preview is None:
            return
        date_str = date.today().strftime("%d_%m_%y")
        parts = [date_str]
        if self._var_counter.get():
            db = self.cfg.get("db_folder", "")
            try:
                n = organizer.next_dia_number(Path(db)) if db and Path(db).is_dir() else 1
            except Exception:
                n = 1
            parts.insert(0, f"Dia{n}")
        letter = self._var_letter.get().strip().upper() or "V"
        if self._var_initial.get():
            parts.append(letter)
        self._lbl_preview.config(text="_".join(parts))

    def _on_initial_var_change(self, *_):
        if hasattr(self, "entry_letter") and self.entry_letter:
            self.entry_letter.config(
                state="normal" if self._var_initial.get() else "disabled"
            )
        self._update_preview()

    def _save_settings(self):
        try:
            slots = int(self._var_slots.get() or "6")
            thresh = int(self._var_thresh.get() or "5")
        except ValueError:
            self._show_result_popup(False, "Valores inválidos. Verifique os campos numéricos.")
            return
        letter = self._var_letter.get().strip().upper() or "V"
        self.cfg["include_day_counter"]    = self._var_counter.get()
        self.cfg["include_person_initial"] = self._var_initial.get()
        self.cfg["person_initial"]         = letter
        self.cfg["slots_per_day"]          = slots
        self.cfg["hash_threshold"]         = thresh
        config.save_config(self.cfg)
        self._var_letter.set(letter)
        self._show_result_popup(True, "Configurações salvas com sucesso!")

    # ------------------------------------------------------------------
    # Pasta de analise
    # ------------------------------------------------------------------

    def _refresh_db_folder_label(self):
        folder = self.cfg.get("db_folder") or ""
        self.lbl_db_folder.config(
            text=folder if folder else "(nenhuma pasta selecionada)",
            fg=TXT_B if folder else TXT_M,
        )

    def choose_db_folder(self):
        folder = filedialog.askdirectory(
            title="Selecione a pasta de destino (seus envios / base de comparacao)"
        )
        if folder:
            self.cfg["db_folder"] = folder
            config.save_config(self.cfg)
            self._refresh_db_folder_label()
            self._update_preview()

    def _refresh_src_folder_label(self):
        folder = getattr(self, "_src_folder", "") or ""
        if hasattr(self, "lbl_src_folder"):
            self.lbl_src_folder.config(
                text=folder if folder else "(nenhuma pasta selecionada)",
                fg=TXT_B if folder else TXT_M,
            )

    def choose_src_folder(self):
        folder = filedialog.askdirectory(
            title="Selecione a pasta da conta de origem (com as publicacoes)"
        )
        if folder:
            self._src_folder = folder
            self._refresh_src_folder_label()

    def _purge_hash_caches(self):
        """Apaga todos os .hashes.json da Pasta de Destino (recursivo), com confirmação."""
        db = self.cfg.get("db_folder")
        if not db or not Path(db).is_dir():
            self._show_toast("Selecione a Pasta de Destino primeiro.", 4000, ERR_BG, ERR_FG)
            return
        if not self._confirm_dialog(
            "Apagar caches de hash",
            "Todos os arquivos .hashes.json dentro da Pasta de Destino serão apagados.\n"
            "Os hashes serão recalculados das imagens reais na próxima comparação "
            "(a primeira ficará um pouco mais lenta). Continuar?",
        ):
            return
        try:
            self.btn_purge_hashes.config(state="disabled")
        except tk.TclError:
            pass

        def worker(root=Path(db)):
            n = dedup.purge_hash_caches(root)

            def fin():
                try:
                    self.btn_purge_hashes.config(state="normal")
                except tk.TclError:
                    pass
                self._show_toast(f"{n} cache(s) de hash apagado(s).", 4000, OK_BG, OK_FG)
            self.after(0, fin)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Logins do Instagram (uma sessao de navegador por funcao)
    # ------------------------------------------------------------------

    _LOGIN_PROFILES = {
        "analysis": lambda: downloader.PROFILE_DIR,
        "feed": lambda: feedbot.PROFILE_DIR,
    }

    def _open_login_browser(self, kind: str):
        """Abre o navegador vinculado a funcao para o usuario logar/deslogar.
        A sessao fica salva no perfil e e usada automaticamente depois."""
        if getattr(self, "_login_browser_busy", False):
            self._show_toast("Feche o navegador de login que já está aberto.", 4000, ERR_BG, ERR_FG)
            return
        if kind == "analysis":
            if getattr(self, "_metrics_busy", False) or str(self.btn_start["state"]) == "disabled":
                self._show_toast("Aguarde o processo que usa este navegador terminar.",
                                 4000, ERR_BG, ERR_FG)
                return
        elif kind == "feed":
            if getattr(self, "_feed_collect_busy", False):
                self._show_toast("Pare a coleta do feed antes de mexer neste login.",
                                 4000, ERR_BG, ERR_FG)
                return
        else:
            return   # publish: inativo por enquanto
        profile = self._LOGIN_PROFILES[kind]()
        self._login_browser_busy = True
        for b in getattr(self, "_login_btns", {}).values():
            try:
                b.config(state="disabled")
            except tk.TclError:
                pass
        self._set_login_status(kind, "abrindo o navegador…")
        threading.Thread(target=self._run_login_browser, args=(kind, profile), daemon=True).start()

    def _set_login_status(self, kind: str, text: str):
        lbl = getattr(self, "_login_status_lbls", {}).get(kind)
        if lbl is not None:
            try:
                lbl.config(text=text)
            except tk.TclError:
                pass

    def _run_login_browser(self, kind: str, profile_dir):
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth

        def status(t):
            self.after(0, lambda: self._set_login_status(kind, t))

        logged = None
        try:
            Path(profile_dir).mkdir(parents=True, exist_ok=True)
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    channel="chrome",
                    headless=False,
                    viewport={"width": 1100, "height": 800},
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    args=["--disable-blink-features=AutomationControlled"],
                )
                Stealth().apply_stealth_sync(ctx)
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                try:
                    page.goto("https://www.instagram.com/",
                              wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass
                # Fica de olho ate o usuario FECHAR a janela do navegador
                while True:
                    try:
                        if not ctx.pages:
                            break
                        logged = downloader._instagram_logged_in(ctx)
                        status(("✓ Sessão ativa" if logged else "✗ Sem login")
                               + " — feche a janela do navegador para concluir")
                        ctx.pages[0].wait_for_timeout(1500)
                    except Exception:
                        break
                try:
                    ctx.close()
                except Exception:
                    pass
            if logged is True:
                status("✓ Sessão salva — esta função vai entrar sozinha nas próximas vezes")
            elif logged is False:
                status("✗ Sem login salvo — a função vai pedir login quando rodar")
            else:
                status("Estado desconhecido — abra de novo para conferir")
        except Exception as exc:
            status(f"Erro ao abrir o navegador: {exc}")
        finally:
            self._login_browser_busy = False

            def fin():
                for k, b in getattr(self, "_login_btns", {}).items():
                    try:
                        b.config(state=("disabled" if k == "publish" else "normal"))
                    except tk.TclError:
                        pass
            self.after(0, fin)

    def start_cross_import(self):
        src = getattr(self, "_src_folder", "")
        if not src or not Path(src).is_dir():
            self._show_result_popup(False, "Selecione a pasta da conta de origem antes de analisar.")
            return
        name = self.entry_list_name.get().strip()
        if not name:
            self._show_result_popup(False, "Dê um nome para a lista antes de analisar.")
            return
        db_folder = self.cfg.get("db_folder")
        if not db_folder or not Path(db_folder).is_dir():
            self._show_result_popup(False, "Selecione a Pasta de Destino (Configurações) antes de analisar.")
            return
        self.btn_cross_start.config(state="disabled")
        self.cross_progress["value"] = 0
        self.cross_lbl_status.config(text="Preparando análise...")
        self._cross_clear_log()
        threading.Thread(
            target=self._run_cross_import, args=(Path(src), name, Path(db_folder)), daemon=True
        ).start()

    def _run_cross_import(self, src_folder: Path, name: str, db_folder: Path):
        try:
            self._cross_log(f"Analisando conta de origem: {src_folder.name}")
            pubs = crossaccount.find_publication_folders(src_folder)
            total = len(pubs)
            if total == 0:
                self._cross_done(False, "Nenhuma publicação encontrada na pasta de origem.")
                return
            self._cross_log(f"{total} publicação(ões) encontrada(s). Comparando com o destino...")
            dest_index = dedup.build_post_index(db_folder)
            threshold = self.cfg.get("hash_threshold", 5)

            items = []
            dup_count = 0
            for i, folder in enumerate(pubs, start=1):
                self._cross_status(f"Analisando a pasta {i} de {total}...", i / total * 100)
                if i == 1 or i == total or i % 10 == 0:
                    self._cross_log(f"  analisando a pasta {i} de {total}")
                images = crossaccount._sorted_images(folder)
                hashes = dedup.hash_new_media(images)
                match = dedup.find_duplicate_post(hashes, dest_index, threshold)
                is_dup = match is not None
                dup_location = self._dup_location_label(match, db_folder) if is_dup else ""
                if is_dup:
                    dup_count += 1
                try:
                    folder_label = str(folder.relative_to(src_folder))
                except ValueError:
                    folder_label = folder.name
                items.append(crossaccount.new_item(
                    folder, folder_label, [str(h) for h in hashes],
                    meta={}, duplicate=is_dup, dup_location=dup_location,
                ))

            list_id = crossaccount.create_list_with_items(name, items)
            self._cross_status("Concluído!", 100)
            self._cross_log(
                f"Lista '{name}' criada: {total} itens "
                f"({dup_count} repetidas em cinza, {total - dup_count} disponíveis)."
            )
            self.after(0, lambda lid=list_id: self._on_cross_imported(lid))
            self._cross_done(True, f"Lista '{name}' criada com {total} publicações.")
        except Exception as exc:
            self._cross_log(f"ERRO: {exc}")
            self._cross_done(False, str(exc))

    # --- helpers de UI do import entre contas (thread-safe) ---

    def _cross_log(self, msg: str):
        self.after(0, lambda: self._cross_log_sync(msg))

    def _cross_log_sync(self, msg: str):
        self.cross_txt_log.config(state="normal")
        self.cross_txt_log.insert("end", msg + "\n")
        self.cross_txt_log.see("end")
        self.cross_txt_log.config(state="disabled")

    def _cross_clear_log(self):
        self.cross_txt_log.config(state="normal")
        self.cross_txt_log.delete("1.0", "end")
        self.cross_txt_log.config(state="disabled")

    def _cross_status(self, text: str, value: float):
        self.after(0, lambda: (
            self.cross_progress.configure(value=value),
            self.cross_lbl_status.config(text=text),
        ))

    def _cross_done(self, success: bool, msg: str):
        def finish():
            self.btn_cross_start.config(state="normal")
            if not success:
                self.cross_progress["value"] = 0
                self.cross_lbl_status.config(text="Erro — veja o LOG")
            self._show_result_popup(success, msg)
        self.after(0, finish)

    def _on_cross_imported(self, list_id: str):
        crossaccount.set_active(list_id)
        if not self._queue_open:
            self._toggle_queue_panel()
        self._refresh_queue_panel_context()

    # ------------------------------------------------------------------
    # Botao Colar / Limpar
    # ------------------------------------------------------------------

    def _on_link_change(self, event=None):
        has = bool(self.entry_link.get().strip())
        self.btn_paste_clear.config(text="Limpar" if has else "Colar")

    def _paste_or_clear(self):
        if self.entry_link.get().strip():
            self.entry_link.delete(0, "end")
            self.btn_paste_clear.config(text="Colar")
        else:
            try:
                text = self.clipboard_get().strip()
                self.entry_link.delete(0, "end")
                self.entry_link.insert(0, text)
                self.btn_paste_clear.config(text="Limpar" if text else "Colar")
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------

    def _log_numbered(self, msg: str):
        self._log_counter += 1
        self.txt_log.config(state="normal")
        if self._log_counter > 1:
            self.txt_log.insert("end", "\n")
        self.txt_log.insert("end", f"[{self._log_counter}] {msg}\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def log(self, msg: str):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", f"  {msg}\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def clear_log(self):
        self._log_counter = 0
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")

    def set_step(self, value: int, label: str = None):
        self.progress["value"] = value
        self.lbl_status.config(text=label if label is not None else STEPS[value])

    # ------------------------------------------------------------------
    # Popup de resultado
    # ------------------------------------------------------------------

    def _show_result_popup(self, success: bool, msg: str):
        self._close_result_popup()
        popup = tk.Toplevel(self)
        self._result_popup = popup
        popup.title("Sucesso" if success else "Aviso")
        popup.resizable(False, False)
        popup.transient(self)
        popup.attributes("-topmost", True)

        bg = OK_BG if success else ERR_BG
        fg = OK_FG if success else ERR_FG
        icon = "✓" if success else "✗"
        popup.configure(bg=bg, cursor="hand2")

        tk.Label(
            popup, text=f"{icon}  {msg}",
            bg=bg, fg=fg, font=FONT_B,
            wraplength=380, padx=24, pady=18, justify="left",
        ).pack()
        tk.Label(
            popup, text="[ clique para fechar ]",
            bg=bg, fg=TXT_M, font=FONT_M,
        ).pack(pady=(0, 10))

        def dismiss(event=None):
            self._close_result_popup(reset_ui=True)

        popup.bind("<Button-1>", dismiss)
        for child in popup.winfo_children():
            child.bind("<Button-1>", dismiss)
        self.bind("<Button-1>", lambda e: dismiss())

        self.update_idletasks()
        w, h = 440, 140
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

    def _close_result_popup(self, reset_ui: bool = False):
        if self._result_popup:
            try:
                self._result_popup.destroy()
            except Exception:
                pass
            self._result_popup = None
            if reset_ui:
                self.clear_log()
                self.progress["value"] = 0
                self.lbl_status.config(text="Aguardando...")
        try:
            self.unbind("<Button-1>")
        except Exception:
            pass

    def _reset_after_duplicate(self):
        """Reset silencioso apos o usuario confirmar repetida no dialog — sem popup extra."""
        self.btn_start.config(state="normal")
        self.btn_paste_clear.config(state="normal")
        self.progress["value"] = 0
        self.lbl_status.config(text="Aguardando...")
        self.clear_log()

    # ------------------------------------------------------------------
    # Dialog de confirmacao
    # ------------------------------------------------------------------

    def _confirm_dialog(self, title: str, message: str) -> bool:
        """Dialog modal com CONFIRMAR / CANCELAR. Retorna True se confirmado."""
        result = tk.BooleanVar(value=False)

        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.configure(bg=PANEL)

        tk.Label(
            dlg, text=message,
            bg=PANEL, fg=TXT_B, font=FONT_B,
            wraplength=320, justify="center",
            padx=28, pady=22,
        ).pack()

        btn_row = tk.Frame(dlg, bg=PANEL)
        btn_row.pack(pady=(0, 20))

        def do_cancel():
            result.set(False)
            dlg.destroy()

        def do_confirm():
            result.set(True)
            dlg.destroy()

        self._btn(btn_row, "CANCELAR",  do_cancel,  "secondary").pack(side="left", padx=(0, 10))
        self._btn(btn_row, "CONFIRMAR", do_confirm, "danger").pack(side="left")

        self.update_idletasks()
        dlg.update_idletasks()
        w, h = 390, 170
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        dlg.wait_window()
        return result.get()

    # ------------------------------------------------------------------
    # Painel de historico
    # ------------------------------------------------------------------

    def _hist_day_key(self, entry: dict) -> str:
        """Chave do dia de um envio: o nome da pasta do dia (Dia.../), ou a data."""
        folder = (entry.get("folder", "") or "").replace("\\", "/")
        if "/" in folder:
            return folder.split("/")[0]
        if folder:
            return folder
        sd = entry.get("save_datetime", "")
        return sd.split(" ")[0] if sd else "?"

    def _hist_day_groups(self, entries: list) -> list:
        """Agrupa os envios por dia e ordena do mais novo para o mais antigo.
        Retorna [(rotulo, [entries]), ...]; a pagina 0 e sempre o dia mais recente."""
        groups = {}
        for e in entries:
            groups.setdefault(self._hist_day_key(e), []).append(e)

        def sortkey(ents):
            sd = ents[0].get("save_datetime", "")  # "DD/MM/YYYY HH:MM"
            try:
                dd, mm, yy = sd.split(" ")[0].split("/")
                return (int(yy), int(mm), int(dd))
            except Exception:
                return (0, 0, 0)

        return sorted(groups.items(), key=lambda kv: sortkey(kv[1]), reverse=True)

    def _group_date(self, ents: list) -> str:
        """Data (DD/MM/YYYY) do primeiro envio de um grupo de dia."""
        sd = ents[0].get("save_datetime", "") if ents else ""
        return sd.split(" ")[0]

    def _hist_pages(self) -> list:
        """Paginas do historico: a pagina 0 e SEMPRE o dia de HOJE (data da maquina).

        Se hoje ainda nao tem envios, a pagina 0 e uma lista em branco virtual e os
        dias anteriores ficam atras dela (seta ◀). A verdade e a DATA, nao a posicao
        na lista — assim a pagina de ontem nunca aparece como editavel de manha."""
        groups = self._hist_day_groups(_load_history())
        today = date.today().strftime("%d/%m/%Y")
        if groups and self._group_date(groups[0][1]) == today:
            return groups
        return [("", [])] + groups   # pagina virtual do hoje em branco

    def _hist_go(self, delta: int):
        pages = self._hist_pages()
        if not pages:
            return
        self._hist_page = max(0, min(self._hist_page + delta, len(pages) - 1))
        self._reload_history_panel()

    def _start_day_watch(self):
        """Vigia leve da virada do dia: a cada 60s compara a data atual com a
        exibida (duas strings — custo zero). A verificacao de verdade acontece em
        todo render; isto so cobre o app aberto parado atravessando a meia-noite."""
        if getattr(self, "_day_watch_on", False):
            return
        self._day_watch_on = True
        self._ui_day = date.today().isoformat()
        self.after(60000, self._day_watch_tick)

    def _day_watch_tick(self):
        try:
            today = date.today().isoformat()
            if today != getattr(self, "_ui_day", today):
                self._ui_day = today
                self._hist_page = 0          # vira para o hoje em branco
                self._reload_history_panel()
        except Exception:
            pass
        self.after(60000, self._day_watch_tick)

    def _reload_history_panel(self):
        inners = [i for i in getattr(self, "_hist_inners", []) if i.winfo_exists()]
        self._hist_inners = inners
        if not inners:
            return
        self._thumb_refs.clear()
        pages = self._hist_pages()
        # Clampa a pagina e escolhe as entradas do dia exibido
        self._hist_page = max(0, min(getattr(self, "_hist_page", 0), len(pages) - 1))
        day_key, page_entries = pages[self._hist_page]
        is_today = (self._hist_page == 0)   # pagina 0 = SEMPRE o hoje real
        day_label = "Lista de Publicações do Dia" if is_today else day_key

        # Atualiza os cabecalhos (rotulo do dia, setas e Resetar) de todos os paineis
        n = len(pages)
        for h in getattr(self, "_hist_headers", []):
            try:
                h["day"].config(text=day_label)
                # ◀ = mais antigo (pagina maior); ▶ = mais novo (pagina 0)
                h["left"].config(fg=(TXT_M if self._hist_page < n - 1 else BORDER),
                                 cursor=("hand2" if self._hist_page < n - 1 else "arrow"))
                h["right"].config(fg=(TXT_M if self._hist_page > 0 else BORDER),
                                  cursor=("hand2" if self._hist_page > 0 else "arrow"))
                # Resetar so existe no HOJE com envios — dias passados sao arquivo
                if "reset" in h:
                    if is_today and page_entries:
                        h["reset"].pack(side="right")
                    else:
                        h["reset"].pack_forget()
            except Exception:
                pass

        for inner in inners:
            for w in inner.winfo_children():
                w.destroy()
            if not page_entries:
                msg = ("Nenhuma publicação hoje ainda." if is_today
                       else "Nenhum envio registrado neste dia.")
                tk.Label(
                    inner, text=msg,
                    fg=TXT_M, font=FONT_B, bg=PANEL,
                ).pack(pady=20, padx=12)
            else:
                for entry in page_entries:   # ordem cronologica (mais recentes embaixo)
                    self._add_history_row(inner, entry, is_today)

    def _delete_history_entry(self, entry: dict):
        entries = _load_history()
        eid = entry.get("id")
        if eid:
            new_entries = [e for e in entries if e.get("id") != eid]
        else:
            # registros antigos sem id: casa por url + data + PASTA (a pasta e unica por slot)
            new_entries = [
                e for e in entries
                if not (e.get("url") == entry.get("url")
                        and e.get("save_datetime") == entry.get("save_datetime")
                        and e.get("folder") == entry.get("folder"))
            ]
        _save_history(new_entries)
        self._reload_history_panel()

    def _cross_src_info(self, entry: dict) -> str:
        """Linha 'de onde veio' para envios do Entre Contas: pasta do dia na conta
        de origem + inicial da outra conta. Vazio para envios por link."""
        origin = entry.get("origin") or {}
        if origin.get("origin") != "cross":
            return ""
        label = origin.get("src_label", "")
        if not label:
            # registros antigos (sem src_label): tenta buscar no item da lista
            it = crossaccount.find_item(origin.get("list_id", ""), origin.get("item_id", ""))
            label = (it or {}).get("folder", "")
        first = label.replace("\\", "/").split("/")[0] if label else ""
        m = organizer.DIA_FOLDER_RE.match(first)
        initial = (m.group(5) or "").upper() if m else ""
        name = origin.get("list_name", "")
        if initial:
            src = f"outra conta ({initial})"
        elif name:
            src = f"outra conta '{name}'"
        else:
            src = "outra conta"
        return f"↪ De {src}: {label}" if label else f"↪ De {src}"

    def _add_history_row(self, parent, entry: dict, is_current: bool = True):
        row_outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        row_outer.pack(fill="x", padx=4, pady=2)
        row = tk.Frame(row_outer, bg=PANEL, padx=8, pady=6)
        row.pack(fill="both", expand=True)

        # Miniatura
        thumb_frame = tk.Frame(
            row, bg=INNER, width=THUMB_SIZE[0] + 4, height=THUMB_SIZE[1] + 4
        )
        thumb_frame.pack(side="left", padx=(0, 10))
        thumb_frame.pack_propagate(False)
        thumb_path = entry.get("thumbnail", "")
        loaded = False
        if thumb_path and Path(thumb_path).exists():
            try:
                img = Image.open(thumb_path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._thumb_refs.append(photo)
                tk.Label(thumb_frame, image=photo, bg=INNER).pack(expand=True)
                loaded = True
            except Exception:
                pass
        if not loaded:
            tk.Label(
                thumb_frame, text="[sem\nimagem]",
                fg=TXT_M, font=FONT_M, justify="center", bg=INNER,
            ).pack(expand=True)

        # Informacoes textuais
        info = tk.Frame(row, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)

        folder   = entry.get("folder", "")
        save_dt  = entry.get("save_datetime", "")
        url      = entry.get("url", "")
        meta     = entry.get("meta", {})

        tk.Label(
            info, text=folder, anchor="w",
            font=FONT_SH, bg=PANEL, fg=TXT_H,
        ).pack(fill="x")
        tk.Label(
            info, text=f"Salva em: {save_dt}", anchor="w",
            font=FONT_S, bg=PANEL, fg=TXT_M,
        ).pack(fill="x")

        # Se veio do Filtro Entre Contas: mostra o dia/pasta na conta de origem
        src_info = self._cross_src_info(entry)
        if src_info:
            tk.Label(
                info, text=src_info, anchor="w",
                font=FONT_S, bg=PANEL, fg=ACCENT,
            ).pack(fill="x")

        meta_row = tk.Frame(info, bg=PANEL)
        meta_row.pack(fill="x", pady=(2, 0))
        for ico, key in [
            (self._ico_eye, "views"),
            (self._ico_heart, "likes"),
            (self._ico_bubble, "comments"),
        ]:
            tk.Label(meta_row, image=ico, bg=PANEL).pack(side="left", padx=(0, 2))
            tk.Label(
                meta_row, text=meta.get(key, "N/D"),
                font=FONT_M, bg=PANEL, fg=TXT_B, anchor="w",
            ).pack(side="left", padx=(0, 10))
        post_date = meta.get("post_date", "N/D")
        if post_date and post_date != "N/D":
            tk.Label(
                meta_row, text=f"Postado em: {post_date}",
                font=FONT_M, bg=PANEL, fg=TXT_M, anchor="w",
            ).pack(side="left")

        # URL + botao de copiar logo ao lado do link
        url_row = tk.Frame(info, bg=PANEL)
        url_row.pack(fill="x", pady=(1, 0))
        url_short = (url[:44] + "...") if len(url) > 47 else url
        url_lbl = tk.Label(
            url_row, text=url_short,
            font=("Consolas", 7), fg=ACCENT, bg=PANEL, anchor="w",
            cursor="hand2",
        )
        url_lbl.pack(side="left")
        url_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        url_lbl.bind("<Enter>", lambda e: url_lbl.config(font=("Consolas", 7, "underline")))
        url_lbl.bind("<Leave>", lambda e: url_lbl.config(font=("Consolas", 7)))
        tk.Button(
            url_row, image=self._ico_copy,
            relief="flat", bd=0, padx=2, pady=0,
            bg=PANEL, activebackground=INNER, cursor="hand2",
            command=lambda u=url: self._copy_to_clipboard(u),
        ).pack(side="left", padx=(4, 0))
        _dbf = self.cfg.get("db_folder", "")
        _folder_path = str(Path(_dbf) / folder) if _dbf and folder else ""
        self._btn(url_row, "📁", lambda p=_folder_path: self._open_folder(p),
                  "secondary_sm").pack(side="left", padx=(4, 0))

        # Canto superior direito (Retornar + apagar) — SO no dia atual.
        # Dias passados sao apenas leitura (arquivados).
        if is_current:
            topright = tk.Frame(row, bg=PANEL)
            topright.place(relx=1.0, rely=0.0, anchor="ne")
            self._btn(
                topright, "↩  Retornar para a Fila",
                lambda ent=entry: self._return_history_to_queue(ent), "secondary_sm",
            ).pack(side="left")
            del_btn = tk.Label(
                topright, text="×",
                font=("Segoe UI", 12, "bold"),
                fg=TXT_M, bg=PANEL, cursor="hand2", padx=4,
            )
            del_btn.pack(side="left", padx=(6, 0))
            del_btn.bind("<Enter>", lambda e: del_btn.config(fg=BDF))
            del_btn.bind("<Leave>", lambda e: del_btn.config(fg=TXT_M))
            del_btn.bind("<Button-1>", lambda e, ent=entry: self._delete_history_entry(ent))

    def _return_history_to_queue(self, entry: dict):
        """Devolve a publicacao para a origem dela.

        - Origem 'cross' (Filtro Entre Contas): esvazia a pasta de envio e marca
          o item da lista como disponivel de novo (volta a ficar colorido).
        - Origem 'link' (padrao): move as imagens de volta para a fila de espera.
        """
        origin = entry.get("origin") or {}
        if origin.get("origin") == "cross":
            self._return_history_to_cross(entry, origin)
            return

        db = self.cfg.get("db_folder")
        folder_label = entry.get("folder", "")
        slot = (Path(db) / folder_label) if db and folder_label else None

        if not slot or not slot.is_dir():
            # Pasta nao existe mais — apenas remove o registro do historico
            self._delete_history_entry(entry)
            self._show_toast("Pasta não encontrada — registro removido.", 4000, ERR_BG, ERR_FG)
            return

        images = dedup._sorted_numbered_images(slot)
        if not images:
            self._delete_history_entry(entry)
            self._show_toast("Sem imagens na pasta — registro removido.", 4000, ERR_BG, ERR_FG)
            return

        # 1) Copia as imagens para a fila (preserva ordem e metadados)
        waitqueue.add_to_queue(entry.get("url", ""), images, entry.get("meta", {}))

        # 2) Esvazia a pasta: apaga as imagens numeradas e o cache de hashes
        for img in images:
            try:
                img.unlink()
            except Exception:
                pass
        cache = slot / dedup._HASH_CACHE
        if cache.exists():
            try:
                cache.unlink()
            except Exception:
                pass

        # 3) Remove do historico e atualiza os paineis
        self._delete_history_entry(entry)
        self._on_queued()  # recarrega/abre a fila
        self._show_toast("Retornado para a Fila de Espera.", 3000, OK_BG, OK_FG)

    def _return_history_to_cross(self, entry: dict, origin: dict):
        """Retorno de um item vindo de uma lista Entre Contas: esvazia a pasta
        de envio e volta o item da lista para 'disponivel' (colorido)."""
        db = self.cfg.get("db_folder")
        folder_label = entry.get("folder", "")
        slot = (Path(db) / folder_label) if db and folder_label else None
        if slot and slot.is_dir():
            for img in dedup._sorted_numbered_images(slot):
                try:
                    img.unlink()
                except Exception:
                    pass
            cache = slot / dedup._HASH_CACHE
            if cache.exists():
                try:
                    cache.unlink()
                except Exception:
                    pass
        # Volta o item da lista para disponivel (colorido)
        crossaccount.set_item_field(origin.get("list_id", ""), origin.get("item_id", ""), "used", False)
        self._delete_history_entry(entry)
        self._refresh_queue_panel_context()
        self._show_toast("Retornado à lista (disponível de novo).", 3000, OK_BG, OK_FG)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._show_toast("Copiado!", 3000, OK_BG, OK_FG)

    def _empty_slot(self, slot):
        """Apaga as imagens numeradas e o cache de hashes de um slot (mantém a Legenda)."""
        if not slot or not slot.is_dir():
            return
        for img in dedup._sorted_numbered_images(slot):
            try:
                img.unlink()
            except Exception:
                pass
        cache = slot / dedup._HASH_CACHE
        if cache.exists():
            try:
                cache.unlink()
            except Exception:
                pass

    def _reset_history(self):
        """Reseta SOMENTE o dia de HOJE, devolvendo cada publicação à sua origem:
        cross → volta pra lista Entre Contas; link da fila → volta pra Fila de Espera;
        link direto → só esvazia a pasta (o usuário cola o link de novo).
        Dias passados são arquivo — nunca são resetáveis."""
        if getattr(self, "_hist_page", 0) != 0:
            self._show_toast("Só a Lista de Publicações do Dia (hoje) pode ser resetada.",
                             4000, ERR_BG, ERR_FG)
            return
        page_entries = self._hist_pages()[0][1]
        if not page_entries:
            self._show_toast("Nenhuma publicação hoje para resetar.", 3500, ERR_BG, ERR_FG)
            return
        if not self._confirm_dialog(
            "Resetar o dia",
            f"Devolver as {len(page_entries)} publicação(ões) de HOJE às suas filas "
            f"de origem e limpar o dia do histórico?\n\n"
            f"As que vieram por link direto NÃO voltam para nenhuma fila — você cola o link de novo.",
        ):
            return

        db = self.cfg.get("db_folder")

        def key(e):
            return e.get("id") or (e.get("url"), e.get("save_datetime"), e.get("folder"))

        for entry in page_entries:
            origin = entry.get("origin") or {}
            kind = origin.get("origin")
            slot = (Path(db) / entry.get("folder", "")) if db and entry.get("folder") else None
            images = dedup._sorted_numbered_images(slot) if (slot and slot.is_dir()) else []
            if kind == "cross":
                crossaccount.set_item_field(origin.get("list_id", ""),
                                            origin.get("item_id", ""), "used", False)
                self._empty_slot(slot)
            elif kind == "link":
                if origin.get("from") == "queue" and images:
                    waitqueue.add_to_queue(entry.get("url", ""), images, entry.get("meta", {}))
                self._empty_slot(slot)  # link direto: só esvazia; usuário recola o link

        remove = {key(e) for e in page_entries}
        remaining = [e for e in _load_history() if key(e) not in remove]
        _save_history(remaining)
        self._reload_history_panel()
        self._refresh_queue_panel_context()
        self._show_toast("Dia resetado — publicações devolvidas às filas.", 3500, OK_BG, OK_FG)

    # ------------------------------------------------------------------
    # Painel da fila de espera
    # ------------------------------------------------------------------

    def _build_queue_panel(self, parent):
        # Divisoria horizontal arrastavel: puxar para a esquerda alarga a fila
        qdiv = tk.Frame(parent, bg=BG, width=14, cursor="sb_h_double_arrow")
        qdiv.pack(side="left", fill="y")
        qdiv.pack_propagate(False)
        qhandle = tk.Frame(qdiv, bg=INNER, highlightbackground=BORDER, highlightthickness=1)
        qhandle.place(relx=0.5, rely=0.5, anchor="center", width=12, height=46)
        qdots = tk.Label(qhandle, text="⋮", font=("Segoe UI", 11, "bold"), bg=INNER, fg=TXT_M)
        qdots.place(relx=0.5, rely=0.5, anchor="center")
        for w in (qdiv, qhandle, qdots):
            w.configure(cursor="sb_h_double_arrow")
            w.bind("<Button-1>", self._queue_drag_start)
            w.bind("<B1-Motion>", self._queue_drag)

        content = tk.Frame(parent, bg=BG)
        content.pack(side="left", fill="both", expand=True)

        self._q_hdr = tk.Frame(content, bg=BG)
        self._q_hdr.pack(fill="x", padx=12, pady=(12, 4))
        self._q_title = tk.Label(
            self._q_hdr, text="SALVOS",
            font=FONT_LBL, bg=BG, fg=TXT_M, anchor="w",
        )
        self._q_title.pack(side="left")
        # Atualizar likes/comentarios da fila via bot (so aparece no modo Filtro
        # por Link — o pack/pack_forget fica em _refresh_queue_panel_context)
        self._q_metrics_btn = self._btn(
            self._q_hdr, "↻ Métricas", self._refresh_queue_metrics, "secondary_sm"
        )
        self._q_metrics_btn.pack(side="right")
        self._q_clear_btn = self._btn(
            self._q_hdr, "Esvaziar", self._clear_waiting_queue, "danger_sm"
        )
        self._q_clear_btn.pack(side="right", padx=(0, 6))

        # Alternador de visao dos Salvos (lista principal x colecoes) — so no modo
        # Filtro por Link; o pack/pack_forget fica em _refresh_queue_panel_context
        if not hasattr(self, "_q_view_mode"):
            self._q_view_mode = "main"     # main | grid | collection
            self._q_view_col = None
        self._q_seg = tk.Frame(content, bg=BG)
        seg_wrap = tk.Frame(self._q_seg, bg=BORDER, padx=1, pady=1)
        seg_wrap.pack(fill="x", padx=12)
        seg_inner = tk.Frame(seg_wrap, bg=INNER)
        seg_inner.pack(fill="x")
        self._q_seg_btns = {}
        for key, label in [("main", "Salvos"), ("grid", "Coleções")]:
            b = tk.Button(
                seg_inner, text=label, font=FONT_S, relief="flat", bd=0,
                cursor="hand2", pady=4, bg=INNER, fg=TXT_M,
                activebackground=INNER, activeforeground=TXT_B,
                command=lambda k=key: self._q_switch_view(k),
            )
            b.pack(side="left", fill="x", expand=True)
            self._q_seg_btns[key] = b

        # Cabecalho da colecao aberta (← nome ✏ 🗑) — montado em _update_col_header
        self._q_col_hdr = tk.Frame(content, bg=BG)

        # Controles do modo 'Entre Contas' (seletor de lista + Recarregar).
        # Ficam ocultos no modo Filtro por Link.
        self._q_controls = tk.Frame(content, bg=BG)
        self._q_list_var = tk.StringVar(value="")
        self._q_list_ids = []
        self._q_list_combo = ttk.Combobox(
            self._q_controls, textvariable=self._q_list_var, state="readonly", font=FONT_S,
        )
        self._q_list_combo.pack(fill="x", padx=12)
        self._q_list_combo.bind("<<ComboboxSelected>>", self._on_cross_list_selected)
        cr_row = tk.Frame(self._q_controls, bg=BG)
        cr_row.pack(fill="x", padx=12, pady=(6, 2))
        self._cross_reload_btn = self._btn(
            cr_row, "↻  Recarregar", self._refresh_cross_list, "secondary_sm")
        self._cross_reload_btn.pack(side="left", fill="x", expand=True)
        self._btn(cr_row, "🗑 Apagar Lista", self._delete_cross_list, "danger_sm").pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )

        # --- Barra de filtros / ordenacao (modo Entre Contas) ---
        if not hasattr(self, "_cf_sort"):
            # As StringVars pertencem a raiz Tk: sobrevivem ao rebuild de tema
            self._cf_sort = tk.StringVar(value="Ordem original")
            self._cf_status = tk.StringVar(value="Todas")
            self._cf_cta = tk.StringVar(value="Todos")
            self._cf_trigger = tk.StringVar(value="")
            self._cf_day_min = tk.StringVar(value="")
            self._cf_day_max = tk.StringVar(value="")
        fbar = tk.Frame(self._q_controls, bg=BG)
        fbar.pack(fill="x", padx=12, pady=(4, 2))
        fbar.columnconfigure(1, weight=1)
        fbar.columnconfigure(3, weight=1)

        def _flbl(r, c, text):
            tk.Label(fbar, text=text, font=FONT_S, bg=BG, fg=TXT_M, anchor="w").grid(
                row=r, column=c, sticky="w", padx=(0, 3)
            )

        _flbl(0, 0, "Ordenar:")
        cb_sort = ttk.Combobox(fbar, textvariable=self._cf_sort, state="readonly",
                               font=FONT_S, values=list(self._CF_SORT_MAP.keys()))
        cb_sort.grid(row=0, column=1, columnspan=3, sticky="we", pady=1)
        _flbl(1, 0, "Status:")
        cb_status = ttk.Combobox(fbar, textvariable=self._cf_status, state="readonly",
                                 font=FONT_S, values=list(self._CF_STATUS_MAP.keys()), width=9)
        cb_status.grid(row=1, column=1, sticky="we", pady=1, padx=(0, 4))
        _flbl(1, 2, "CTA:")
        cb_cta = ttk.Combobox(fbar, textvariable=self._cf_cta, state="readonly",
                              font=FONT_S, values=list(self._CF_CTA_MAP.keys()), width=9)
        cb_cta.grid(row=1, column=3, sticky="we", pady=1)
        _flbl(2, 0, "Gatilho:")
        en_trig = tk.Entry(fbar, textvariable=self._cf_trigger, font=FONT_S, width=9,
                           bg=INNER, fg=TXT_H, insertbackground=TXT_H, relief="flat", bd=0)
        en_trig.grid(row=2, column=1, sticky="we", pady=1, padx=(0, 4), ipady=2)
        _flbl(2, 2, "Dia:")
        day_wrap = tk.Frame(fbar, bg=BG)
        day_wrap.grid(row=2, column=3, sticky="we")
        vcmd_day = (self.register(lambda v: v == "" or (v.isdigit() and len(v) <= 3)), "%P")
        en_dmin = tk.Entry(day_wrap, textvariable=self._cf_day_min, font=FONT_S, width=4,
                           justify="center", bg=INNER, fg=TXT_H, insertbackground=TXT_H,
                           relief="flat", bd=0, validate="key", validatecommand=vcmd_day)
        en_dmin.pack(side="left", ipady=2)
        tk.Label(day_wrap, text="a", font=FONT_S, bg=BG, fg=TXT_M).pack(side="left", padx=3)
        en_dmax = tk.Entry(day_wrap, textvariable=self._cf_day_max, font=FONT_S, width=4,
                           justify="center", bg=INNER, fg=TXT_H, insertbackground=TXT_H,
                           relief="flat", bd=0, validate="key", validatecommand=vcmd_day)
        en_dmax.pack(side="left", ipady=2)

        ffoot = tk.Frame(fbar, bg=BG)
        ffoot.grid(row=3, column=0, columnspan=4, sticky="we", pady=(3, 0))
        self._btn(ffoot, "Limpar filtros", self._clear_cross_filters, "secondary_sm").pack(side="left")
        self._cf_count_lbl = tk.Label(ffoot, text="", font=FONT_S, bg=BG, fg=TXT_M)
        self._cf_count_lbl.pack(side="right")

        for cb in (cb_sort, cb_status, cb_cta):
            cb.bind("<<ComboboxSelected>>", self._on_cross_filter_change)
        for en in (en_trig, en_dmin, en_dmax):
            en.bind("<KeyRelease>", self._on_cross_filter_typed)

        q_outer = tk.Frame(content, bg=BORDER, padx=1, pady=1)
        q_outer.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._q_outer = q_outer   # referencia p/ posicionar o cabecalho de colecao
        q_card = tk.Frame(q_outer, bg=PANEL)
        q_card.pack(fill="both", expand=True)

        self._queue_canvas = tk.Canvas(
            q_card, borderwidth=0, highlightthickness=0, bg=PANEL
        )
        sb_q = ttk.Scrollbar(q_card, orient="vertical", command=self._queue_yview)
        self._queue_canvas.configure(yscrollcommand=sb_q.set)

        self._queue_inner = tk.Frame(self._queue_canvas, bg=PANEL)
        self._queue_inner_id = self._queue_canvas.create_window(
            (0, 0), window=self._queue_inner, anchor="nw"
        )
        self._queue_canvas.pack(side="left", fill="both", expand=True)
        sb_q.pack(side="right", fill="y")

        self._queue_inner.bind(
            "<Configure>",
            lambda e: self._queue_canvas.configure(scrollregion=self._queue_canvas.bbox("all")),
        )
        self._queue_canvas.bind("<Configure>", self._on_queue_canvas_configure)
        self._queue_canvas.bind(
            "<Enter>",
            lambda e: self._queue_canvas.bind_all("<MouseWheel>", self._on_queue_scroll),
        )
        self._queue_canvas.bind(
            "<Leave>", lambda e: self._queue_canvas.unbind_all("<MouseWheel>")
        )
        self._queue_thumb_refs: list = []
        self._q_state = []          # [{id, frame, h, y, ty}] em ordem de exibicao
        self._q_drag = None         # {id, grab_dy} enquanto arrasta
        self._q_anim_running = False

    def _on_queue_scroll(self, event):
        self._queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        if getattr(self, "_tab_active", "") == "cross":
            self._cross_virtual_update()

    def _queue_yview(self, *args):
        """Scrollbar da fila: rola e, no modo Entre Contas, atualiza a janela virtual."""
        self._queue_canvas.yview(*args)
        if getattr(self, "_tab_active", "") == "cross":
            self._cross_virtual_update()

    def _on_queue_canvas_configure(self, event):
        self._queue_canvas.itemconfigure(self._queue_inner_id, width=event.width)
        if getattr(self, "_tab_active", "") == "cross":
            self._cross_virtual_update()
        elif getattr(self, "_q_view_mode", "main") == "grid":
            # Grade de colecoes: re-render coalescido p/ os mosaicos acompanharem
            # a nova largura (bandeja/janela redimensionada)
            if getattr(self, "_q_grid_rr", None):
                try:
                    self.after_cancel(self._q_grid_rr)
                except Exception:
                    pass
            self._q_grid_rr = self.after(200, self._q_grid_rerender)

    def _q_grid_rerender(self):
        self._q_grid_rr = None
        if (getattr(self, "_tab_active", "link") == "link"
                and getattr(self, "_q_view_mode", "main") == "grid"):
            self._reload_queue_panel()

    def _reload_queue_panel(self):
        """Painel dos Salvos: despacha para a visao ativa (Salvos, grade de
        Coleções ou uma coleção aberta — estilo 'Salvos' do Instagram)."""
        if not hasattr(self, "_queue_inner"):
            return
        self._update_q_seg_styles()
        self._update_col_header()
        mode = getattr(self, "_q_view_mode", "main")
        self._q_drag = None
        for w in self._queue_inner.winfo_children():
            w.destroy()
        self._queue_thumb_refs.clear()
        self._q_state = []
        if mode == "grid":
            self._render_collections_grid()
            return
        all_entries = waitqueue.load_queue()
        if mode == "collection":
            entries = waitqueue.collection_entries(getattr(self, "_q_view_col", ""), all_entries)
            draggable = False   # reordenacao por arraste so na lista principal
            empty_msg = "Coleção vazia.\nUse o 🔖 nos cartões dos Salvos\npara adicionar publicações."
        else:
            entries = waitqueue.main_entries(all_entries)
            draggable = True
            empty_msg = "Nenhuma publicação salva."
        if not entries:
            self._queue_inner.configure(height=100)
            tk.Label(
                self._queue_inner, text=empty_msg,
                fg=TXT_M, font=FONT_B, bg=PANEL,
                wraplength=240, justify="center",
            ).place(x=12, y=16)
            return
        for entry in entries:
            frame = self._build_queue_row(entry, draggable=draggable)
            self._q_state.append({
                "id": entry.get("id", ""), "frame": frame,
                "h": 0, "y": 0.0, "ty": 0.0,
            })
        # Mede a altura real de cada cartao apos montar o conteudo, depois posiciona
        self._queue_inner.update_idletasks()
        for st in self._q_state:
            st["h"] = max(st["frame"].winfo_reqheight(), 1)
        self._q_relayout(initial=True)

    # --- Salvos: alternador de visao, grade de colecoes e cabecalho ---

    def _q_switch_view(self, key: str):
        self._q_view_mode = "main" if key == "main" else "grid"
        self._q_view_col = None
        self._reload_queue_panel()

    def _q_open_collection(self, col_id: str):
        self._q_view_mode = "collection"
        self._q_view_col = col_id
        self._reload_queue_panel()

    def _update_q_seg_styles(self):
        mode = getattr(self, "_q_view_mode", "main")
        active_key = "main" if mode == "main" else "grid"
        for k, b in getattr(self, "_q_seg_btns", {}).items():
            act = (k == active_key)
            try:
                b.config(bg=ACCENT if act else INNER,
                         fg="#FFFFFF" if act else TXT_M,
                         activebackground=ACCENT if act else INNER,
                         activeforeground="#FFFFFF" if act else TXT_B)
            except tk.TclError:
                pass

    def _update_col_header(self):
        """Monta o cabecalho '← Nome ✏ 🗑' quando uma colecao esta aberta."""
        hdr = getattr(self, "_q_col_hdr", None)
        if hdr is None:
            return
        for w in hdr.winfo_children():
            w.destroy()
        if getattr(self, "_q_view_mode", "main") != "collection":
            hdr.pack_forget()
            return
        col = next((c for c in waitqueue.load_collections()
                    if c.get("id") == getattr(self, "_q_view_col", None)), None)
        if col is None:   # colecao sumiu (apagada) → volta pra grade
            self._q_view_mode = "grid"
            self._q_view_col = None
            hdr.pack_forget()
            return
        back = tk.Label(hdr, text="←", font=("Segoe UI", 12, "bold"),
                        bg=BG, fg=TXT_M, cursor="hand2")
        back.pack(side="left", padx=(0, 6))
        back.bind("<Button-1>", lambda e: self._q_switch_view("grid"))
        tk.Label(hdr, text=col.get("name", "?"), font=FONT_SH, bg=BG,
                 fg=TXT_H, anchor="w").pack(side="left", fill="x", expand=True)
        self._btn(hdr, "🗑", lambda cid=col["id"]: self._delete_collection_flow(cid),
                  "danger_sm").pack(side="right")
        self._btn(hdr, "✏", lambda cid=col["id"]: self._rename_collection_flow(cid),
                  "secondary_sm").pack(side="right", padx=(0, 4))
        if not hdr.winfo_ismapped():
            hdr.pack(fill="x", padx=12, pady=(0, 4), before=self._q_outer)

    def _collection_mosaic(self, entries: list, size: int = 132):
        """Mosaico 2x2 (estilo Salvos do Instagram): capas de ate 4 publicacoes."""
        img = Image.new("RGB", (size, size), INNER)
        half = size // 2
        pos = [(0, 0), (half, 0), (0, half), (half, half)]
        for i, e in enumerate(entries[:4]):
            tp = e.get("thumbnail", "")
            if not tp or not Path(tp).exists():
                continue
            try:
                t = Image.open(tp).convert("RGB")
                w, h = t.size
                m = min(w, h)
                t = t.crop(((w - m) // 2, (h - m) // 2,
                            (w - m) // 2 + m, (h - m) // 2 + m))
                t = t.resize((half, half), Image.LANCZOS)
                img.paste(t, pos[i])
            except Exception:
                pass
        return ImageTk.PhotoImage(img)

    def _render_collections_grid(self):
        """Grade 2 colunas de colecoes: quadrado com mosaico 2x2 + nome + contagem.
        O respiro e uniforme (borda esq = vao central = borda dir) e os mosaicos
        se dimensionam pela largura disponivel do painel."""
        inner = self._queue_inner
        inner.columnconfigure(0, weight=1, uniform="qcols")
        inner.columnconfigure(1, weight=1, uniform="qcols")
        gap = GRID_GAP
        avail = self._queue_canvas.winfo_width()
        if avail < 60:   # canvas ainda sem layout: assume a largura minima do painel
            avail = QUEUE_MIN_W - 24
        tsize = max(100, min((avail - 3 * gap) // 2, 260))
        cols = waitqueue.load_collections()
        all_entries = waitqueue.load_queue()
        self._btn(inner, "+  Nova Coleção", self._create_collection_flow,
                  "secondary_sm").grid(row=0, column=0, columnspan=2,
                                       sticky="we", padx=gap, pady=(gap - 4, 6))
        if not cols:
            tk.Label(
                inner, text="Nenhuma coleção ainda.\nCrie a primeira!",
                fg=TXT_M, font=FONT_B, bg=PANEL, justify="center",
            ).grid(row=1, column=0, columnspan=2, pady=16)
        for i, col in enumerate(cols):
            ents = waitqueue.collection_entries(col.get("id", ""), all_entries)
            tile = tk.Frame(inner, bg=PANEL, cursor="hand2")
            # metade do vao em cada tile: borda = gap e centro = gap/2 + gap/2
            padx = (gap, gap // 2) if i % 2 == 0 else (gap // 2, gap)
            tile.grid(row=1 + i // 2, column=i % 2, padx=padx, pady=6, sticky="n")
            photo = self._collection_mosaic(ents, size=tsize)
            self._queue_thumb_refs.append(photo)
            img_wrap = tk.Frame(tile, bg=BORDER, padx=1, pady=1)
            img_wrap.pack()
            img_lbl = tk.Label(img_wrap, image=photo, bg=INNER)
            img_lbl.pack()
            name_lbl = tk.Label(tile, text=col.get("name", "?"), font=FONT_SH,
                                bg=PANEL, fg=TXT_H)
            name_lbl.pack(anchor="w", pady=(4, 0))
            cnt_lbl = tk.Label(tile, text=f"{len(ents)} publicação(ões)",
                               font=FONT_S, bg=PANEL, fg=TXT_M)
            cnt_lbl.pack(anchor="w")
            for w in (tile, img_lbl, name_lbl, cnt_lbl):
                w.bind("<Button-1>", lambda e, cid=col.get("id", ""): self._q_open_collection(cid))
        inner.update_idletasks()
        inner.configure(height=max(inner.winfo_reqheight(), 100))

    def _create_collection_flow(self):
        name = self._ask_text("Nova Coleção", "Nome da coleção:")
        if not name:
            return
        waitqueue.create_collection(name)
        self._q_view_mode = "grid"
        self._reload_queue_panel()
        self._refresh_q_dest_combo_safe()
        self._show_toast(f"Coleção '{name}' criada.", 3000, OK_BG, OK_FG)

    def _rename_collection_flow(self, col_id: str):
        col = next((c for c in waitqueue.load_collections() if c.get("id") == col_id), None)
        if col is None:
            return
        name = self._ask_text("Renomear Coleção", "Novo nome:", col.get("name", ""))
        if not name:
            return
        waitqueue.rename_collection(col_id, name)
        self._reload_queue_panel()
        self._refresh_q_dest_combo_safe()
        self._show_toast("Coleção renomeada.", 2500, OK_BG, OK_FG)

    def _delete_collection_flow(self, col_id: str):
        col = next((c for c in waitqueue.load_collections() if c.get("id") == col_id), None)
        if col is None:
            return
        if not self._confirm_dialog(
            "Apagar coleção",
            f"A coleção '{col.get('name', '?')}' será apagada.\n"
            "As publicações NÃO são apagadas — as que estavam só nela "
            "voltam para os Salvos. Continuar?",
        ):
            return
        waitqueue.delete_collection(col_id)
        self._q_view_mode = "grid"
        self._q_view_col = None
        self._reload_queue_panel()
        self._refresh_q_dest_combo_safe()
        self._show_toast("Coleção apagada.", 3000, OK_BG, OK_FG)

    def _ask_text(self, title: str, prompt: str, initial: str = ""):
        """Dialog modal com um campo de texto. Retorna o texto ou None."""
        result = [None]
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.configure(bg=PANEL)
        tk.Label(dlg, text=prompt, bg=PANEL, fg=TXT_B, font=FONT_B).pack(
            padx=26, pady=(18, 6))
        wrap = tk.Frame(dlg, bg=BORDER, padx=1, pady=1)
        wrap.pack(fill="x", padx=26)
        ent = tk.Entry(wrap, font=FONT_B, bg=INNER, fg=TXT_H,
                       insertbackground=TXT_H, relief="flat", bd=0)
        ent.pack(fill="x", ipady=4)
        ent.insert(0, initial)
        ent.focus_set()
        ent.select_range(0, "end")
        btn_row = tk.Frame(dlg, bg=PANEL)
        btn_row.pack(pady=(14, 18))

        def ok(event=None):
            result[0] = ent.get().strip() or None
            dlg.destroy()

        ent.bind("<Return>", ok)
        self._btn(btn_row, "CANCELAR", dlg.destroy, "secondary").pack(side="left", padx=(0, 10))
        self._btn(btn_row, "OK", ok, "primary").pack(side="left")
        self.update_idletasks()
        dlg.update_idletasks()
        w, h = 380, 160
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.wait_window()
        return result[0]

    def _edit_entry_collections(self, entry: dict):
        """Dialog 🔖 'Salvar em Coleções' de uma publicacao, com a opcao de
        tirar dos Salvos (deixar SO nas colecoes marcadas)."""
        dlg = tk.Toplevel(self)
        dlg.title("Salvar em Coleções")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.configure(bg=PANEL)
        tk.Label(dlg, text="Escolha as coleções desta publicação:",
                 bg=PANEL, fg=TXT_B, font=FONT_B).pack(padx=24, pady=(16, 8))
        box = tk.Frame(dlg, bg=PANEL)
        box.pack(fill="both", expand=True, padx=24)
        var_by_id = {}
        hint = [None]

        def add_check(col, checked):
            v = tk.BooleanVar(value=checked)
            var_by_id[col.get("id", "")] = v
            tk.Checkbutton(
                box, text=col.get("name", "?"), variable=v, font=FONT_B,
                bg=PANEL, fg=TXT_B, activebackground=PANEL,
                activeforeground=TXT_H, selectcolor=PANEL,
                anchor="w", cursor="hand2",
            ).pack(fill="x")

        current = set(entry.get("collections") or [])
        cols = waitqueue.load_collections()
        if not cols:
            hint[0] = tk.Label(box, text="Nenhuma coleção ainda — crie abaixo.",
                               font=FONT_S, bg=PANEL, fg=TXT_M, anchor="w")
            hint[0].pack(fill="x", pady=(0, 4))
        for c in cols:
            add_check(c, c.get("id", "") in current)

        # Criar nova colecao sem sair do dialog
        new_row = tk.Frame(dlg, bg=PANEL)
        new_row.pack(fill="x", padx=24, pady=(8, 0))
        nwrap = tk.Frame(new_row, bg=BORDER, padx=1, pady=1)
        nwrap.pack(side="left", fill="x", expand=True)
        ent_new = tk.Entry(nwrap, font=FONT_B, bg=INNER, fg=TXT_H,
                           insertbackground=TXT_H, relief="flat", bd=0)
        ent_new.pack(fill="x", ipady=3)

        def create_new(event=None):
            name = ent_new.get().strip()
            if not name:
                return
            col = waitqueue.create_collection(name)
            if hint[0] is not None:
                try:
                    hint[0].destroy()
                except Exception:
                    pass
                hint[0] = None
            add_check(col, True)
            ent_new.delete(0, "end")
            self._refresh_q_dest_combo_safe()
            dlg.update_idletasks()
            dlg.geometry(f"{dlg.winfo_width()}x{dlg.winfo_reqheight()}"
                         f"+{dlg.winfo_x()}+{dlg.winfo_y()}")

        ent_new.bind("<Return>", create_new)
        self._btn(new_row, "+ Criar", create_new, "secondary_sm").pack(side="left", padx=(6, 0))

        only_var = tk.BooleanVar(value=bool(entry.get("only_collections")))
        tk.Checkbutton(
            dlg, text="Tirar dos Salvos (deixar SÓ nas coleções marcadas)",
            variable=only_var, font=FONT_S, bg=PANEL, fg=TXT_B,
            activebackground=PANEL, activeforeground=TXT_H,
            selectcolor=PANEL, anchor="w", cursor="hand2", wraplength=320,
        ).pack(fill="x", padx=24, pady=(10, 0))

        btn_row = tk.Frame(dlg, bg=PANEL)
        btn_row.pack(pady=(12, 16))

        def save():
            ids = [cid for cid, v in var_by_id.items() if v.get()]
            if only_var.get() and not ids:
                self._show_toast("Marque ao menos uma coleção para tirar dos Salvos.",
                                 4000, ERR_BG, ERR_FG)
                return
            waitqueue.set_entry_collections(entry.get("id", ""), ids, only_var.get())
            dlg.destroy()
            self._reload_queue_panel()
            self._show_toast("Coleções atualizadas.", 2500, OK_BG, OK_FG)

        self._btn(btn_row, "CANCELAR", dlg.destroy, "secondary").pack(side="left", padx=(0, 10))
        self._btn(btn_row, "SALVAR", save, "primary").pack(side="left")
        self.update_idletasks()
        dlg.update_idletasks()
        w = max(dlg.winfo_reqwidth(), 400)
        h = dlg.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

    def _build_queue_row(self, entry: dict, draggable: bool = True):
        """Monta o cartao de um item (sem posiciona-lo) e retorna o frame externo.
        draggable=False nas visoes de colecao (reordenar so na lista principal)."""
        entry_id = entry.get("id", "")
        row_outer = tk.Frame(self._queue_inner, bg=BORDER, padx=1, pady=1)
        row = tk.Frame(row_outer, bg=PANEL, padx=8, pady=8)
        row.pack(fill="both", expand=True)

        top = tk.Frame(row, bg=PANEL)
        top.pack(fill="x")

        # Miniatura
        thumb_frame = tk.Frame(
            top, bg=INNER, width=THUMB_SIZE[0] + 4, height=THUMB_SIZE[1] + 4
        )
        thumb_frame.pack(side="left", padx=(0, 8))
        thumb_frame.pack_propagate(False)
        thumb_path = entry.get("thumbnail", "")
        loaded = False
        if thumb_path and Path(thumb_path).exists():
            try:
                img = Image.open(thumb_path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._queue_thumb_refs.append(photo)
                tk.Label(thumb_frame, image=photo, bg=INNER).pack(expand=True)
                loaded = True
            except Exception:
                pass
        if not loaded:
            tk.Label(
                thumb_frame, text="[sem\nimagem]",
                fg=TXT_M, font=FONT_M, justify="center", bg=INNER,
            ).pack(expand=True)

        # Informacoes
        info = tk.Frame(top, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(
            info, text=entry.get("shortcode") or "publicação", anchor="w",
            font=FONT_SH, bg=PANEL, fg=TXT_H,
        ).pack(fill="x", padx=(0, 18))  # espaco a direita p/ a alca de arraste
        tk.Label(
            info, text=entry.get("queue_datetime", ""), anchor="w",
            font=FONT_S, bg=PANEL, fg=TXT_M,
        ).pack(fill="x")

        meta = entry.get("meta", {})
        meta_row = tk.Frame(info, bg=PANEL)
        meta_row.pack(fill="x", pady=(2, 0))
        row_outer._meta_labels = {}   # p/ atualizar so estes rotulos no ↻ Métricas
        for ico, key in [
            (self._ico_eye, "views"),
            (self._ico_heart, "likes"),
            (self._ico_bubble, "comments"),
        ]:
            tk.Label(meta_row, image=ico, bg=PANEL).pack(side="left", padx=(0, 2))
            val_lbl = tk.Label(
                meta_row, text=meta.get(key, "N/D"),
                font=FONT_M, bg=PANEL, fg=TXT_B, anchor="w",
            )
            val_lbl.pack(side="left", padx=(0, 8))
            row_outer._meta_labels[key] = val_lbl
        # 'Postado em:' em linha propria — na mesma linha das metricas cortava
        post_date = meta.get("post_date", "N/D")
        if post_date and post_date != "N/D":
            tk.Label(
                info, text=f"Postado em: {post_date}",
                font=FONT_M, bg=PANEL, fg=TXT_M, anchor="w",
            ).pack(fill="x")

        # URL clicavel (sem botao de copiar)
        url = entry.get("url", "")
        url_short = (url[:34] + "...") if len(url) > 37 else url
        url_lbl = tk.Label(
            row, text=url_short,
            font=("Consolas", 7), fg=ACCENT, bg=PANEL, anchor="w", cursor="hand2",
        )
        url_lbl.pack(fill="x", pady=(4, 0))
        url_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        url_lbl.bind("<Enter>", lambda e: url_lbl.config(font=("Consolas", 7, "underline")))
        url_lbl.bind("<Leave>", lambda e: url_lbl.config(font=("Consolas", 7)))

        # Botoes de acao
        btns = tk.Frame(row, bg=PANEL)
        btns.pack(fill="x", pady=(8, 0))
        self._btn(
            btns, "Utilizar de Próxima",
            lambda ent=entry: self._use_queue_entry(ent), "green_sm",
        ).pack(side="left")
        self._btn(
            btns, "🔖",
            lambda ent=entry: self._edit_entry_collections(ent), "secondary_sm",
        ).pack(side="left", padx=(4, 0))
        # Dentro de uma colecao: materializar na PASTA da colecao (sequencias)
        if getattr(self, "_q_view_mode", "main") == "collection":
            self._btn(
                btns, "📂 Pasta",
                lambda ent=entry: self._send_entry_to_collection_folder(ent),
                "secondary_sm",
            ).pack(side="left", padx=(4, 0))
        self._btn(
            btns, "Remover da Espera",
            lambda ent=entry: self._remove_queue_entry(ent), "danger_sm",
        ).pack(side="right")

        if draggable:
            # Alca de arraste (so o simbolo), no canto superior direito do cartao
            grip = tk.Label(
                row, text="⠿", font=("Segoe UI", 14, "bold"),
                bg=PANEL, fg=TXT_M, cursor="fleur",
            )
            grip.place(relx=1.0, y=0, anchor="ne")
            grip.bind("<Button-1>", lambda e, i=entry_id: self._q_drag_start(e, i))
            grip.bind("<B1-Motion>", self._q_drag_motion)
            grip.bind("<ButtonRelease-1>", lambda e, i=entry_id: self._q_drag_release(e, i))

        return row_outer

    def _use_queue_entry(self, entry: dict):
        db = self.cfg.get("db_folder")
        if not db or not Path(db).is_dir():
            self._show_toast("Selecione a pasta de análise primeiro.", 4000, ERR_BG, ERR_FG)
            return
        db_folder = Path(db)
        images = waitqueue.entry_images(entry)
        if not images:
            self._show_toast("Imagens não encontradas — item removido.", 4000, ERR_BG, ERR_FG)
            waitqueue.remove_from_queue(entry.get("id", ""))
            self._reload_queue_panel()
            return

        initial     = self.cfg.get("person_initial", "Z")
        slots       = self.cfg.get("slots_per_day", 4)
        inc_counter = self.cfg.get("include_day_counter", True)
        inc_initial = self.cfg.get("include_person_initial", True)

        day_folder = organizer.ensure_day_folder(
            db_folder, initial, slots, inc_counter, inc_initial
        )
        slot = organizer.find_next_empty_slot(day_folder, slots)
        if slot is None:
            self._show_toast(
                f"Não há pasta livre hoje em '{day_folder.name}'.", 4000, ERR_BG, ERR_FG
            )
            return

        organizer.save_media_to_slot(slot, images)
        self._record_history(entry.get("url", ""), slot, entry.get("meta", {}),
                             origin={"origin": "link", "from": "queue"})
        waitqueue.remove_from_queue(entry.get("id", ""))
        self._reload_queue_panel()
        slot_label = str(slot.relative_to(db_folder))
        self._show_toast(f"Enviado para {slot_label}", 3000, OK_BG, OK_FG)

    def _remove_queue_entry(self, entry: dict):
        waitqueue.remove_from_queue(entry.get("id", ""))
        self._reload_queue_panel()
        self._show_toast("Removido da fila de espera.", 3000, ERR_BG, ERR_FG)

    def _clear_waiting_queue(self):
        """Esvazia a Fila de Espera inteira (remove itens + apaga imagens estacionadas)."""
        if getattr(self, "_metrics_busy", False):
            self._show_toast("Aguarde a atualização de métricas terminar.", 4000, ERR_BG, ERR_FG)
            return
        entries = waitqueue.load_queue()
        if not entries:
            self._show_toast("A fila já está vazia.", 3000, ERR_BG, ERR_FG)
            return
        if not self._confirm_dialog(
            "Esvaziar Fila de Espera",
            f"As {len(entries)} publicação(ões) da fila serão removidas e as imagens "
            "estacionadas apagadas. Continuar?",
        ):
            return
        for e in entries:
            waitqueue.remove_from_queue(e.get("id", ""))
        self._reload_queue_panel()
        self._show_toast("Fila de espera esvaziada.", 3000, OK_BG, OK_FG)

    # ------------------------------------------------------------------
    # Fila: atualizar curtidas/comentarios via bot (link por link)
    # ------------------------------------------------------------------

    def _refresh_queue_metrics(self):
        """Abre o navegador e visita cada link da fila para recapturar as metricas.
        Pede confirmacao antes — o sistema fica ocupado durante o processo."""
        if getattr(self, "_metrics_busy", False):
            return
        if str(self.btn_start["state"]) == "disabled":
            self._show_toast("Aguarde o processo atual terminar.", 4000, ERR_BG, ERR_FG)
            return
        pairs = [(e.get("id", ""), e.get("url", ""))
                 for e in waitqueue.load_queue() if e.get("url")]
        if not pairs:
            self._show_toast("A fila não tem publicações com link.", 4000, ERR_BG, ERR_FG)
            return
        if not self._confirm_dialog(
            "Atualizar métricas da fila",
            f"O navegador será aberto e visitará {len(pairs)} publicação(ões), uma por uma, "
            "para atualizar curtidas e comentários.\n"
            "O sistema ficará ocupado durante o processo. Continuar?",
        ):
            return
        self._metrics_busy = True
        try:
            self._q_metrics_btn.config(state="disabled", text="↻ Atualizando…")
        except tk.TclError:
            pass
        self._log_async(f"Atualizando curtidas/comentários de {len(pairs)} publicação(ões) da fila…")
        threading.Thread(target=self._run_queue_metrics, args=(pairs,), daemon=True).start()

    def _run_queue_metrics(self, pairs: list):
        ids = [i for i, _ in pairs]
        urls = [u for _, u in pairs]
        updated = [0]

        def on_meta(i, url, meta):
            if not meta or all(v in ("", "N/D", None) for v in meta.values()):
                self._log_async(f"  {i + 1}/{len(urls)}: não foi possível capturar (login?) — valores mantidos")
                return
            entries = waitqueue.load_queue()   # recarrega: a fila pode ter mudado no meio
            for e in entries:
                if e.get("id") == ids[i]:
                    m = e.setdefault("meta", {})
                    for k, v in meta.items():
                        if v and v != "N/D":   # falha pontual nao apaga valor antigo
                            m[k] = v
                    waitqueue.save_queue(entries)
                    updated[0] += 1
                    self._log_async(
                        f"  {i + 1}/{len(urls)}: curtidas {m.get('likes', 'N/D')} · "
                        f"comentários {m.get('comments', 'N/D')}"
                    )
                    self.after(0, lambda eid=e["id"], mm=dict(m): self._apply_queue_meta(eid, mm))
                    return
            self._log_async(f"  {i + 1}/{len(urls)}: item saiu da fila — ignorado")

        try:
            downloader.fetch_meta_batch(urls, progress_cb=self._log_async, on_meta=on_meta,
                                        login_wait_cb=self._login_wait_cb)
            self._log_async(f"Métricas atualizadas: {updated[0]} de {len(urls)}.")
        except Exception as exc:
            self._log_async(f"ERRO ao atualizar métricas: {exc}")
        finally:
            self._metrics_busy = False

            def fin():
                try:
                    self._q_metrics_btn.config(state="normal", text="↻ Métricas")
                except tk.TclError:
                    pass
                if getattr(self, "_tab_active", "link") == "link":
                    self._reload_queue_panel()
            self.after(0, fin)

    def _apply_queue_meta(self, entry_id: str, meta: dict):
        """Reativo: reconfigura so os rotulos de metricas do cartao daquele item."""
        for st in getattr(self, "_q_state", []):
            if st.get("id") == entry_id:
                labels = getattr(st.get("frame"), "_meta_labels", None) or {}
                for k, lbl in labels.items():
                    try:
                        lbl.config(text=meta.get(k, "N/D"))
                    except tk.TclError:
                        pass
                return

    # --- Aviso de login no Instagram (o bot pausa e espera o usuario entrar) ---

    def _login_wait_cb(self, active: bool):
        """Chamado pelo downloader (thread) quando o bot fica aguardando login."""
        self.after(0, self._show_login_popup if active else self._close_login_popup)

    def _show_login_popup(self):
        self._close_login_popup()
        pop = tk.Toplevel(self)
        self._login_popup = pop
        pop.title("Login no Instagram")
        pop.resizable(False, False)
        pop.transient(self)
        pop.attributes("-topmost", True)
        pop.configure(bg=PANEL)
        tk.Label(pop, text="🔐  Login necessário", font=FONT_H, bg=PANEL, fg=TXT_H).pack(
            padx=28, pady=(20, 6)
        )
        tk.Label(
            pop,
            text="Para capturar curtidas e comentários, faça login no Instagram\n"
                 "na janela do Chrome que o robô abriu.\n\n"
                 "O processo continua sozinho assim que o login for detectado\n"
                 "(aguarda até 5 minutos — sem login, segue sem as métricas).",
            font=FONT_B, bg=PANEL, fg=TXT_B, justify="center",
        ).pack(padx=28, pady=(0, 18))
        self.update_idletasks()
        pop.update_idletasks()
        w = max(pop.winfo_reqwidth(), 380)
        h = max(pop.winfo_reqheight(), 140)
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        pop.geometry(f"{w}x{h}+{x}+{y}")

    def _close_login_popup(self):
        pop = getattr(self, "_login_popup", None)
        if pop is not None:
            try:
                pop.destroy()
            except Exception:
                pass
            self._login_popup = None

    # ------------------------------------------------------------------
    # Fila: posicionamento e arraste suave (estilo edicao de playlist)
    # ------------------------------------------------------------------

    _Q_GAP = 6  # espaco vertical entre cartoes

    def _q_relayout(self, initial: bool = False):
        """Recalcula a posicao-alvo (ty) de cada item empilhado, deixando um vao
        para o item que esta sendo arrastado (ele segue o cursor)."""
        drag_id = self._q_drag["id"] if self._q_drag else None
        y = 0.0
        for st in self._q_state:
            if st["id"] == drag_id:
                y += st["h"] + self._Q_GAP  # reserva o vao do item arrastado
                continue
            st["ty"] = y
            if initial:
                st["y"] = y
                st["frame"].place(x=0, y=int(y), relwidth=1)
            y += st["h"] + self._Q_GAP
        self._queue_inner.configure(height=max(int(y) + 2, 1))
        if not initial:
            self._q_start_anim()

    def _q_start_anim(self):
        if self._q_anim_running:
            return
        self._q_anim_running = True
        self._q_tick()

    def _q_tick(self):
        state = getattr(self, "_q_state", [])
        if not state:
            self._q_anim_running = False
            return
        drag_id = self._q_drag["id"] if self._q_drag else None
        still = False
        for st in state:
            if st["id"] == drag_id:
                continue  # posicionado diretamente pelo cursor
            dy = st["ty"] - st["y"]
            if abs(dy) > 0.5:
                st["y"] += dy * 0.35  # easing suave
                still = True
            else:
                st["y"] = st["ty"]
            try:
                st["frame"].place(x=0, y=int(st["y"]), relwidth=1)
            except Exception:
                pass
        if still or self._q_drag:
            self.after(16, self._q_tick)  # ~60fps
        else:
            self._q_anim_running = False

    def _q_drag_start(self, event, entry_id):
        st = next((s for s in self._q_state if s["id"] == entry_id), None)
        if not st:
            return
        inner_y = event.y_root - self._queue_inner.winfo_rooty()
        self._q_drag = {"id": entry_id, "grab_dy": inner_y - st["y"]}
        st["frame"].lift()
        self._q_relayout()
        self._q_start_anim()

    def _q_drag_motion(self, event):
        if not self._q_drag:
            return
        st = next((s for s in self._q_state if s["id"] == self._q_drag["id"]), None)
        if not st:
            return
        inner_y = event.y_root - self._queue_inner.winfo_rooty()
        new_y = max(0.0, inner_y - self._q_drag["grab_dy"])
        st["y"] = new_y
        try:
            st["frame"].place(x=0, y=int(new_y), relwidth=1)
        except Exception:
            pass
        self._q_reorder_by_center(new_y + st["h"] / 2)

    def _q_reorder_by_center(self, center: float):
        drag_id = self._q_drag["id"]
        order = [s["id"] for s in self._q_state]
        y = 0.0
        target = 0
        for s in self._q_state:
            if s["id"] == drag_id:
                continue
            if center > y + s["h"] / 2:
                target += 1
            y += s["h"] + self._Q_GAP
        non = [s for s in self._q_state if s["id"] != drag_id]
        dragged = next(s for s in self._q_state if s["id"] == drag_id)
        target = max(0, min(target, len(non)))
        new_state = non[:target] + [dragged] + non[target:]
        if [s["id"] for s in new_state] != order:
            self._q_state = new_state
            self._q_relayout()

    def _q_drag_release(self, event, entry_id):
        if not self._q_drag:
            return
        self._q_drag = None
        # Define o alvo final de todos (inclusive o solto) para assentar com easing
        y = 0.0
        for st in self._q_state:
            st["ty"] = y
            y += st["h"] + self._Q_GAP
        self._queue_inner.configure(height=max(int(y) + 2, 1))
        self._q_start_anim()
        # Persiste a nova ordem na fila
        order = [s["id"] for s in self._q_state]
        entries = waitqueue.load_queue()
        by_id = {e.get("id"): e for e in entries}
        new_entries = [by_id[i] for i in order if i in by_id]
        for e in entries:
            if e.get("id") not in order:
                new_entries.append(e)
        waitqueue.save_queue(new_entries)

    def _find_first_image(self, folder: Path):
        for name in ("raw_1", "1"):
            for ext in ("jpg", "jpeg", "png", "webp"):
                p = folder / f"{name}.{ext}"
                if p.exists():
                    return p
        return None

    def _show_duplicate_dialog(
        self,
        new_folder: Path,
        existing_folder: Path,
        info_text: str,
        decision: list,
        event: threading.Event,
        title: str = "Publicacao Repetida Detectada",
        col2_title: str = "Post ja enviado",
        cancel_label: str = "Confirmar Repetida",
        proceed_label: str = "Nao e Repetida — Salvar Mesmo Assim",
    ):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=ERR_BG)

        IMG_W, IMG_H = 170, 170
        # Refs ficam em self para sobreviver alem do retorno da funcao (evita GC do PhotoImage)
        self._dup_img_refs = []

        tk.Label(
            dlg, text=title,
            font=FONT_H, bg=ERR_BG, fg=ERR_FG, pady=12,
        ).pack()

        imgs_row = tk.Frame(dlg, bg=ERR_BG)
        imgs_row.pack(padx=20, pady=4)

        def make_img_col(parent, title, img_path):
            col = tk.Frame(parent, bg=ERR_BG)
            col.pack(side="left", padx=10)
            tk.Label(col, text=title, font=FONT_M, bg=ERR_BG, fg=ERR_FG).pack(pady=(0, 4))
            frame = tk.Frame(col, bg=BORDER, padx=1, pady=1)
            frame.pack()
            inner = tk.Frame(frame, bg=INNER, width=IMG_W, height=IMG_H)
            inner.pack()
            inner.pack_propagate(False)
            if img_path and img_path.exists():
                try:
                    img = Image.open(img_path)
                    img.thumbnail((IMG_W, IMG_H), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self._dup_img_refs.append(photo)
                    tk.Label(inner, image=photo, bg=INNER).pack(expand=True)
                except Exception:
                    tk.Label(inner, text="[erro ao\ncarregar]", fg=TXT_M, font=FONT_S, bg=INNER, justify="center").pack(expand=True)
            else:
                tk.Label(inner, text="[sem\nimagem]", fg=TXT_M, font=FONT_S, bg=INNER, justify="center").pack(expand=True)

        make_img_col(imgs_row, "Nova publicacao", self._find_first_image(new_folder))
        make_img_col(imgs_row, col2_title, self._find_first_image(existing_folder))

        tk.Label(
            dlg,
            text=info_text,
            font=FONT_S, bg=ERR_BG, fg=ERR_FG,
        ).pack(pady=(10, 14))

        btn_row = tk.Frame(dlg, bg=ERR_BG)
        btn_row.pack(pady=(0, 18))

        def confirm_dup(e=None):
            try:
                self.unbind("<Button-1>")
            except Exception:
                pass
            decision[0] = "duplicate"
            if dlg.winfo_exists():
                dlg.destroy()
            event.set()

        def save_anyway():
            try:
                self.unbind("<Button-1>")
            except Exception:
                pass
            decision[0] = "save"
            if dlg.winfo_exists():
                dlg.destroy()
            event.set()

        dlg.protocol("WM_DELETE_WINDOW", confirm_dup)
        self._btn(btn_row, cancel_label, confirm_dup, "secondary").pack(side="left", padx=(0, 10))
        self._btn(btn_row, proceed_label, save_anyway, "primary").pack(side="left")
        # Clicar na tela principal = cancelar (mesmo comportamento do balao de resultado)
        self.bind("<Button-1>", lambda e: confirm_dup())

        dlg.update_idletasks()
        w = dlg.winfo_reqwidth()
        h = dlg.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        dlg.geometry(f"+{x}+{y}")

    def _record_history(self, url: str, slot: Path, ig_meta: dict = None, origin: dict = None):
        thumb_path = ""
        for ext in ("jpg", "jpeg", "png", "webp"):
            p = slot / f"1.{ext}"
            if p.exists():
                thumb_path = str(p)
                break

        db_folder = Path(self.cfg.get("db_folder", ""))
        try:
            folder_label = str(slot.relative_to(db_folder))
        except ValueError:
            folder_label = slot.name

        default_meta = {"views": "N/D", "likes": "N/D", "comments": "N/D", "post_date": "N/D"}
        entry = {
            "id": uuid.uuid4().hex,   # identidade unica (evita apagar itens irmaos)
            "url": url,
            "save_datetime": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "folder": folder_label,
            "thumbnail": thumb_path,
            "meta": {**default_meta, **(ig_meta or {})},
            "origin": origin or {"origin": "link", "from": "direct"},
        }
        entries = _load_history()
        entries.append(entry)   # novos entram no fim (timeline: mais recentes embaixo)
        _save_history(entries)
        self.after(0, self._reload_history_panel)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _build_queue_index(self):
        """Indice de hashes das publicacoes que estao na fila de espera,
        no mesmo formato que dedup.build_post_index (lista de (pasta, hashes))."""
        index = []
        for q in waitqueue.load_queue():
            d = waitqueue.WAITING_DIR / q.get("id", "")
            if d.is_dir():
                hs = dedup.get_all_hashes(d)
                if hs:
                    index.append((d, hs))
        return index

    def _ask_match(self, new_folder, matched_folder, info_text,
                   title, col2_title, cancel_label, proceed_label) -> bool:
        """Mostra o dialog lado a lado e bloqueia ate o usuario decidir.
        Retorna True se o usuario optar por prosseguir (proceed)."""
        dec_event = threading.Event()
        decision = ["cancel"]
        self.after(0, lambda: self._show_duplicate_dialog(
            new_folder, matched_folder, info_text, decision, dec_event,
            title, col2_title, cancel_label, proceed_label,
        ))
        dec_event.wait()
        return decision[0] == "save"

    def start_pipeline(self):
        if getattr(self, "_metrics_busy", False):
            self._show_result_popup(False, "Aguarde a atualização de métricas da fila terminar.")
            return
        link = self.entry_link.get().strip()
        if not link:
            self._show_result_popup(False, "Cole o link da publicação do Instagram antes de iniciar.")
            return
        db_folder = self.cfg.get("db_folder")
        if not db_folder or not Path(db_folder).is_dir():
            self._show_result_popup(False, "Selecione a pasta de análise antes de iniciar.")
            return
        mode = getattr(self, "_var_mode", "use")
        # Colecao de destino escolhida no 'Salvar em:' (le AQUI, na thread da UI)
        dest_col = None
        if mode == "queue" and hasattr(self, "_q_dest_combo"):
            idx = self._q_dest_combo.current()
            if 0 <= idx < len(self._q_dest_ids):
                dest_col = self._q_dest_ids[idx]
            if dest_col == "__new__":
                dest_col = None
        self.btn_start.config(state="disabled")
        self.btn_paste_clear.config(state="disabled")
        self.progress["value"] = 0
        self.lbl_status.config(text=STEPS[0])
        self.clear_log()
        threading.Thread(
            target=self._run_pipeline, args=(link, Path(db_folder), mode, dest_col),
            daemon=True,
        ).start()

    def _run_pipeline(self, link: str, db_folder: Path, mode: str = "use",
                      dest_col: "str | None" = None,
                      feed_mark: "tuple | None" = None):
        tmp_dir = Path(tempfile.mkdtemp(prefix="instabot_"))
        try:
            self._step(0, "Verificando configuracoes...")
            initial     = self.cfg.get("person_initial", "Z")
            slots       = self.cfg.get("slots_per_day", 4)
            threshold   = self.cfg.get("hash_threshold", 5)
            inc_counter = self.cfg.get("include_day_counter", True)
            inc_initial = self.cfg.get("include_person_initial", True)

            # Para "usar agora" precisamos de uma pasta livre ja nesta etapa.
            # Para a fila de espera nao — a publicacao so e estacionada.
            slot = None
            if mode == "use":
                self._step(1, "Preparando pasta do dia...")
                day_folder = organizer.ensure_day_folder(
                    db_folder, initial, slots, inc_counter, inc_initial
                )
                slot = organizer.find_next_empty_slot(day_folder, slots)
                if slot is None:
                    raise RuntimeError(
                        f"Todos os {slots} envios de hoje ja foram preenchidos em '{day_folder.name}'."
                    )
            else:
                self._step(1, "Preparando fila de espera...")

            self._step(2, "Baixando midias do snapinsta.to...")
            media_paths, ig_meta = downloader.download_carousel(
                link, tmp_dir, progress_cb=lambda m: self._log_async(m),
                login_wait_cb=self._login_wait_cb,
            )

            proceed_label = (
                "Não é Repetida — Enfileirar Mesmo Assim" if mode == "queue"
                else "Nao e Repetida — Salvar Mesmo Assim"
            )

            # --- 1) Checa o historico de envios ---
            self._step(3, "Verificando repeticoes...")
            post_index = dedup.build_post_index(db_folder)
            new_hashes = dedup.hash_new_media(media_paths)
            self._log_async(
                f"  {len(new_hashes)} img(s) novas · {len(post_index)} post(s) no historico"
            )
            duplicate = dedup.find_duplicate_post(new_hashes, post_index, threshold)
            if not duplicate and post_index:
                self._log_async(f"  Nao repetida — {dedup.best_match_stats(new_hashes, post_index, threshold)}")
            if duplicate:
                existing_folder, max_dist = duplicate
                try:
                    folder_label = str(existing_folder.relative_to(db_folder))
                except ValueError:
                    folder_label = existing_folder.name
                info = f"Pasta: {folder_label}   |   distancia hash: {max_dist}"
                proceed = self._ask_match(
                    tmp_dir, existing_folder, info,
                    "Publicacao Repetida Detectada", "Post ja enviado",
                    "Confirmar Repetida", proceed_label,
                )
                if not proceed:
                    self.after(0, self._reset_after_duplicate)
                    return

            # --- 2) Checa a fila de espera (o card final sempre difere; tolerancia ja aplicada) ---
            matched_queue_id = None
            queue_index = self._build_queue_index()
            q_match = dedup.find_duplicate_post(new_hashes, queue_index, threshold)
            if q_match:
                q_dir, q_dist = q_match
                matched_queue_id = q_dir.name
                self._log_async(f"  Tambem encontrada na fila de espera (dist {q_dist}).")
                proceed = self._ask_match(
                    tmp_dir, q_dir,
                    "Esta publicação já está aguardando na Fila de Espera.",
                    "Já está na Fila de Espera", "Aguardando na fila",
                    "Cancelar",
                    "Enfileirar Mesmo Assim" if mode == "queue" else "Usar Mesmo Assim",
                )
                if not proceed:
                    self.after(0, self._reset_after_duplicate)
                    return

            if mode == "queue":
                self._step(4, "Adicionando à fila de espera...")
                q_entry = waitqueue.add_to_queue(link, media_paths, ig_meta)
                if dest_col:   # 'Salvar em: Salvos + colecao' escolhido no dropdown
                    waitqueue.set_entry_collections(q_entry.get("id", ""), [dest_col], False)
                    self._log_async("Salva tambem na colecao escolhida.")
                if feed_mark:  # veio do Feed Especial: marca salva e sai do feed
                    feedinbox.set_item_status(feed_mark[0], feed_mark[1], "saved")
                    self.after(0, lambda: self._reload_feed_view(keep_scroll=True))
                self._step(5, "Adicionado à fila de espera!")
                self._log_async("Publicacao estacionada na fila de espera.")
                self.after(0, self._on_queued)
                self._done_queue()
                return

            self._step(4, "Salvando arquivos na pasta de envio...")
            organizer.save_media_to_slot(slot, media_paths)

            # Estava na fila e foi usada agora — remove da fila para nao reutilizar depois
            if matched_queue_id:
                waitqueue.remove_from_queue(matched_queue_id)
                self._log_async("Removida da fila de espera (foi utilizada agora).")
                self.after(0, self._reload_queue_panel)

            self._step(5, "Concluido!")
            slot_label = str(slot.relative_to(db_folder))
            self._log_async(f"Publicacao salva em: {slot_label}")
            likes = ig_meta.get("likes", "N/D")
            if likes != "N/D":
                self._log_async(f"Dados: {likes} curtidas · {ig_meta.get('comments', 'N/D')} comentarios")
            else:
                self._log_async("Dados do post: faca login no Instagram no navegador do bot para capturar")
            self._done(True, f"Publicacao salva com sucesso!\n{slot_label}", link, slot, ig_meta)

        except Exception as exc:
            self._log_async(f"ERRO: {exc}")
            self._done(False, str(exc), link, None)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Atualizacoes de UI thread-safe
    # ------------------------------------------------------------------

    def _step(self, value: int, text: str):
        self.after(0, lambda: (self.set_step(value, text), self._log_numbered(text)))

    def _log_async(self, msg: str):
        self.after(0, lambda: self.log(msg))

    def _done(self, success: bool, msg: str, link: str = "", slot: "Path | None" = None, ig_meta: dict = None):
        def finish():
            self.btn_start.config(state="normal")
            self.btn_paste_clear.config(state="normal")
            if success:
                self.entry_link.delete(0, "end")
                self.btn_paste_clear.config(text="Colar")
                if slot:
                    self._record_history(link, slot, ig_meta or {})
            else:
                self.progress["value"] = 0
                self.lbl_status.config(text="Erro — veja o LOG abaixo")
            self._show_result_popup(success, msg)

        self.after(0, finish)

    def _done_queue(self):
        def finish():
            self.btn_start.config(state="normal")
            self.btn_paste_clear.config(state="normal")
            self.entry_link.delete(0, "end")
            self.btn_paste_clear.config(text="Colar")
            self._show_result_popup(True, "Publicação adicionada à fila de espera!")

        self.after(0, finish)

    def _on_queued(self):
        # Publicacao nova entra nos Salvos — volta pra visao principal p/ aparecer
        self._q_view_mode = "main"
        self._q_view_col = None
        if self._queue_open:
            self._reload_queue_panel()
        else:
            self._toggle_queue_panel()  # abre o painel (ja recarrega ao abrir)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
