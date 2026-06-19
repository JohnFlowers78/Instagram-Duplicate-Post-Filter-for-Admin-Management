import json
import re
import shutil
import tempfile
import threading
import tkinter as tk
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageDraw, ImageTk

import config
import dedup
import downloader
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

QUEUE_W = 320        # largura do painel da fila de espera quando aberto

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
        self.geometry("620x760")
        self.minsize(560, 560)
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
        self._var_letter  = tk.StringVar(value=self.cfg.get("person_initial", "V"))
        self._var_slots   = tk.StringVar(value=str(self.cfg.get("slots_per_day", 6)))
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

        for key, label in [("main", "  Filtro  "), ("settings", "  Configurações  ")]:
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
            ("main",     self._build_main_tab),
            ("settings", self._build_settings_tab),
        ]:
            page = tk.Frame(self._left, bg=BG)
            self._tab_pages[key] = page
            build_fn(page)

        self._switch_tab("main")

    def _switch_tab(self, name: str):
        for k in self._tab_pages:
            self._tab_pages[k].pack_forget()
            self._tab_btns[k].configure(fg=TXT_M, font=FONT_B)
            self._tab_inds[k].configure(bg=PANEL)
        self._tab_pages[name].pack(fill="both", expand=True)
        self._tab_btns[name].configure(fg=ACCENT, font=FONT_SH)
        self._tab_inds[name].configure(bg=ACCENT)
        self._tab_active = name

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
        # btn_start pode ainda nao existir (durante o build) ou apontar para um
        # widget ja destruido (durante a reconstrucao de tema) — protege ambos.
        btn = getattr(self, "btn_start", None)
        if btn is not None:
            try:
                btn.config(text="Adicionar à Fila" if mode == "queue" else "Iniciar")
            except tk.TclError:
                pass

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
            self._queue_panel.configure(width=self._queue_w)
            self._queue_panel.pack(side="right", fill="y")
            self._btn_queue_toggle.config(text="❮")
            self._queue_open = True
            self._reload_queue_panel()
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
        min_w = 240
        max_w = self.winfo_width() - 360  # garante espaco para a UI principal
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
    # Aba principal
    # ------------------------------------------------------------------

    def _build_main_tab(self, page):
        PAD = {"padx": 12, "pady": (6, 0)}

        # Card: pasta de analise
        outer, card = self._make_card(page, "Pasta de Análise")
        outer.pack(fill="x", **PAD)
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x")
        self.lbl_db_folder = tk.Label(
            row, text="(nenhuma pasta selecionada)",
            font=FONT_B, bg=PANEL, fg=TXT_M, anchor="w",
        )
        self.lbl_db_folder.pack(side="left", fill="x", expand=True)
        self._btn(row, "Selecionar...", self.choose_db_folder, "secondary").pack(
            side="right", padx=(10, 0)
        )

        # Card: nova publicacao
        outer2, card2 = self._make_card(page, "Nova Publicação do Instagram")
        outer2.pack(fill="x", **PAD)

        # Chave seletora: usar agora x adicionar a fila de espera
        self._var_mode = "use"
        self._mode_btns = {}
        mode_row = tk.Frame(card2, bg=BORDER, padx=1, pady=1)
        mode_row.pack(fill="x", pady=(0, 8))
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
        self._set_mode("use")

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
        self.btn_start = self._btn(link_row, "Iniciar", self.start_pipeline, "primary")
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

        # --- Historico (preenche o espaco restante) ---
        hist_holder = tk.Frame(split, bg=BG)
        hist_holder.pack(fill="both", expand=True, side="top")

        hist_hdr = tk.Frame(hist_holder, bg=BG)
        hist_hdr.pack(fill="x", padx=12, pady=(0, 2))
        tk.Label(
            hist_hdr, text="HISTÓRICO DE ENVIOS",
            font=FONT_LBL, bg=BG, fg=TXT_M, anchor="w",
        ).pack(side="left")
        self._btn(hist_hdr, "Resetar", self._reset_history, "danger_sm").pack(side="right")

        hist_outer = tk.Frame(hist_holder, bg=BORDER, padx=1, pady=1)
        hist_outer.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        hist_card = tk.Frame(hist_outer, bg=PANEL)
        hist_card.pack(fill="both", expand=True)

        self._hist_canvas = tk.Canvas(
            hist_card, borderwidth=0, highlightthickness=0, height=120, bg=PANEL
        )
        sb_hist = ttk.Scrollbar(hist_card, orient="vertical", command=self._hist_canvas.yview)
        self._hist_canvas.configure(yscrollcommand=sb_hist.set)

        self._hist_inner = tk.Frame(self._hist_canvas, bg=PANEL)
        self._hist_inner_id = self._hist_canvas.create_window(
            (0, 0), window=self._hist_inner, anchor="nw"
        )
        self._hist_canvas.pack(side="left", fill="both", expand=True)
        sb_hist.pack(side="right", fill="y")

        self._hist_inner.bind(
            "<Configure>",
            lambda e: self._hist_canvas.configure(scrollregion=self._hist_canvas.bbox("all")),
        )
        self._hist_canvas.bind(
            "<Configure>",
            lambda e: self._hist_canvas.itemconfigure(self._hist_inner_id, width=e.width),
        )
        self._hist_canvas.bind(
            "<Enter>",
            lambda e: self._hist_canvas.bind_all("<MouseWheel>", self._on_hist_scroll),
        )
        self._hist_canvas.bind(
            "<Leave>", lambda e: self._hist_canvas.unbind_all("<MouseWheel>")
        )

    # ------------------------------------------------------------------
    # Aba configuracoes
    # ------------------------------------------------------------------

    def _build_settings_tab(self, page):
        PAD = {"padx": 12, "pady": (10, 0)}

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
            title="Selecione a pasta onde estao os envios anteriores"
        )
        if folder:
            self.cfg["db_folder"] = folder
            config.save_config(self.cfg)
            self._refresh_db_folder_label()
            self._update_preview()

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

    def _on_hist_scroll(self, event):
        self._hist_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _reload_history_panel(self):
        for w in self._hist_inner.winfo_children():
            w.destroy()
        self._thumb_refs.clear()
        entries = _load_history()
        if not entries:
            tk.Label(
                self._hist_inner,
                text="Nenhum envio registrado ainda.",
                fg=TXT_M, font=FONT_B, bg=PANEL,
            ).pack(pady=20, padx=12)
            return
        for entry in entries:
            self._add_history_row(entry)

    def _delete_history_entry(self, entry: dict):
        entries = _load_history()
        new_entries = [
            e for e in entries
            if not (e.get("url") == entry.get("url") and
                    e.get("save_datetime") == entry.get("save_datetime"))
        ]
        _save_history(new_entries)
        self._reload_history_panel()

    def _add_history_row(self, entry: dict):
        row_outer = tk.Frame(self._hist_inner, bg=BORDER, padx=1, pady=1)
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

        # Canto superior direito (sobreposto — nao reserva coluna): Retornar + apagar.
        # Fica fixo a direita e visivel mesmo com a UI principal estreitada.
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
        """Move as imagens da pasta de envio de volta para a fila de espera.

        Remove as imagens (e o cache .hashes.json) da pasta, deixando-a livre de
        novo, e re-enfileira a publicacao para uso posterior.
        """
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

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._show_toast("Copiado!", 3000, OK_BG, OK_FG)

    def _reset_history(self):
        if not self._confirm_dialog(
            "Resetar Histórico",
            "Deseja realmente apagar todo o histórico de envios?\n\nEsta ação não pode ser desfeita.",
        ):
            return
        _save_history([])
        self._reload_history_panel()

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

        hdr = tk.Frame(content, bg=BG)
        hdr.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(
            hdr, text="FILA DE ESPERA",
            font=FONT_LBL, bg=BG, fg=TXT_M, anchor="w",
        ).pack(side="left")

        q_outer = tk.Frame(content, bg=BORDER, padx=1, pady=1)
        q_outer.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        q_card = tk.Frame(q_outer, bg=PANEL)
        q_card.pack(fill="both", expand=True)

        self._queue_canvas = tk.Canvas(
            q_card, borderwidth=0, highlightthickness=0, bg=PANEL
        )
        sb_q = ttk.Scrollbar(q_card, orient="vertical", command=self._queue_canvas.yview)
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
        self._queue_canvas.bind(
            "<Configure>",
            lambda e: self._queue_canvas.itemconfigure(self._queue_inner_id, width=e.width),
        )
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

    def _reload_queue_panel(self):
        if not hasattr(self, "_queue_inner"):
            return
        self._q_drag = None
        for w in self._queue_inner.winfo_children():
            w.destroy()
        self._queue_thumb_refs.clear()
        self._q_state = []
        entries = waitqueue.load_queue()
        if not entries:
            self._queue_inner.configure(height=80)
            tk.Label(
                self._queue_inner,
                text="Nenhuma publicação na fila.",
                fg=TXT_M, font=FONT_B, bg=PANEL,
                wraplength=240, justify="center",
            ).place(x=12, y=16)
            return
        for entry in entries:
            frame = self._build_queue_row(entry)
            self._q_state.append({
                "id": entry.get("id", ""), "frame": frame,
                "h": 0, "y": 0.0, "ty": 0.0,
            })
        # Mede a altura real de cada cartao apos montar o conteudo, depois posiciona
        self._queue_inner.update_idletasks()
        for st in self._q_state:
            st["h"] = max(st["frame"].winfo_reqheight(), 1)
        self._q_relayout(initial=True)

    def _build_queue_row(self, entry: dict):
        """Monta o cartao de um item (sem posiciona-lo) e retorna o frame externo."""
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
        for ico, key in [
            (self._ico_eye, "views"),
            (self._ico_heart, "likes"),
            (self._ico_bubble, "comments"),
        ]:
            tk.Label(meta_row, image=ico, bg=PANEL).pack(side="left", padx=(0, 2))
            tk.Label(
                meta_row, text=meta.get(key, "N/D"),
                font=FONT_M, bg=PANEL, fg=TXT_B, anchor="w",
            ).pack(side="left", padx=(0, 8))
        post_date = meta.get("post_date", "N/D")
        if post_date and post_date != "N/D":
            tk.Label(
                meta_row, text=f"Postado em: {post_date}",
                font=FONT_M, bg=PANEL, fg=TXT_M, anchor="w",
            ).pack(side="left")

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
            btns, "Remover da Espera",
            lambda ent=entry: self._remove_queue_entry(ent), "danger_sm",
        ).pack(side="right")

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

        initial     = self.cfg.get("person_initial", "V")
        slots       = self.cfg.get("slots_per_day", 6)
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
        self._record_history(entry.get("url", ""), slot, entry.get("meta", {}))
        waitqueue.remove_from_queue(entry.get("id", ""))
        self._reload_queue_panel()
        slot_label = str(slot.relative_to(db_folder))
        self._show_toast(f"Enviado para {slot_label}", 3000, OK_BG, OK_FG)

    def _remove_queue_entry(self, entry: dict):
        waitqueue.remove_from_queue(entry.get("id", ""))
        self._reload_queue_panel()
        self._show_toast("Removido da fila de espera.", 3000, ERR_BG, ERR_FG)

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

    def _record_history(self, url: str, slot: Path, ig_meta: dict = None):
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
            "url": url,
            "save_datetime": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "folder": folder_label,
            "thumbnail": thumb_path,
            "meta": {**default_meta, **(ig_meta or {})},
        }
        entries = _load_history()
        entries.insert(0, entry)
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
        link = self.entry_link.get().strip()
        if not link:
            self._show_result_popup(False, "Cole o link da publicação do Instagram antes de iniciar.")
            return
        db_folder = self.cfg.get("db_folder")
        if not db_folder or not Path(db_folder).is_dir():
            self._show_result_popup(False, "Selecione a pasta de análise antes de iniciar.")
            return
        mode = getattr(self, "_var_mode", "use")
        self.btn_start.config(state="disabled")
        self.btn_paste_clear.config(state="disabled")
        self.progress["value"] = 0
        self.lbl_status.config(text=STEPS[0])
        self.clear_log()
        threading.Thread(
            target=self._run_pipeline, args=(link, Path(db_folder), mode), daemon=True
        ).start()

    def _run_pipeline(self, link: str, db_folder: Path, mode: str = "use"):
        tmp_dir = Path(tempfile.mkdtemp(prefix="instabot_"))
        try:
            self._step(0, "Verificando configuracoes...")
            initial     = self.cfg.get("person_initial", "V")
            slots       = self.cfg.get("slots_per_day", 6)
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
                link, tmp_dir, progress_cb=lambda m: self._log_async(m)
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
                waitqueue.add_to_queue(link, media_paths, ig_meta)
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
        if self._queue_open:
            self._reload_queue_panel()
        else:
            self._toggle_queue_panel()  # abre o painel (ja recarrega ao abrir)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
