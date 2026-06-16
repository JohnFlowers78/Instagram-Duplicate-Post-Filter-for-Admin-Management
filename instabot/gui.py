import json
import re
import shutil
import tempfile
import threading
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageDraw, ImageTk

import config
import dedup
import downloader
import organizer
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

BG     = "#EEEAE5"   # fundo principal — bege quente
PANEL  = "#FFFFFF"   # cartoes/paineis — branco
INNER  = "#F7F5F2"   # fundos internos
BORDER = "#D9D4CE"   # bordas sutis
TXT_H  = "#1C1917"   # texto principal — quase preto
TXT_B  = "#44403C"   # corpo — cinza escuro quente
TXT_M  = "#9C9590"   # texto secundario — cinza medio
ACCENT = "#0D9488"   # teal vibrante — cor de destaque
OK_BG  = "#DCFCE7"   # fundo sucesso
OK_FG  = "#14532D"   # texto sucesso
ERR_BG = "#FEE2E2"   # fundo erro
ERR_FG = "#991B1B"   # texto erro
BPF    = "#1C1917"   # botao primario — fundo
BPT    = "#FFFFFF"   # botao primario — texto
BSF    = "#E8E4DF"   # botao secundario — fundo
BST    = "#1C1917"   # botao secundario — texto
BDF    = "#DC2626"   # botao perigo — fundo
BDT    = "#FFFFFF"   # botao perigo — texto

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
        c = (100, 100, 100, 255)
        d.arc([0, s // 4, s - 1, s * 3 // 4 - 1], start=180, end=360, fill=c, width=1)
        d.arc([0, s // 4, s - 1, s * 3 // 4 - 1], start=0, end=180, fill=c, width=1)
        r = max(1, s // 6)
        cx, cy = s // 2, s // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return _make_icon(draw, size)


def _icon_heart(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (100, 100, 100, 255)
        h = s // 2
        d.arc([0, 0, h, h], start=180, end=360, fill=c, width=1)
        d.arc([h - 2, 0, s - 1, h], start=180, end=360, fill=c, width=1)
        q = h // 2
        d.line([(0, q), (s // 2, s - 1)], fill=c, width=1)
        d.line([(s - 1, q), (s // 2, s - 1)], fill=c, width=1)
    return _make_icon(draw, size)


def _icon_bubble(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (100, 100, 100, 255)
        tail = max(2, s // 4)
        d.ellipse([0, 0, s - 1, s - 1 - tail], outline=c, width=1)
        d.polygon([(1, s - tail - 1), (0, s - 1), (tail + 1, s - tail - 1)], fill=c)
    return _make_icon(draw, size)


def _icon_copy(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (100, 100, 100, 255)
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
        self.title("Filtro de Repetidas - Instagram")
        self.geometry("620x760")
        self.minsize(560, 560)
        self.resizable(True, True)
        self.configure(bg=BG)

        self.cfg = config.load_config()
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

        self._ico_eye    = _icon_eye()
        self._ico_heart  = _icon_heart()
        self._ico_bubble = _icon_bubble()
        self._ico_copy   = _icon_copy()

        # Variaveis de configuracao (aba Configuracoes)
        self._var_counter = tk.BooleanVar(value=self.cfg.get("include_day_counter", True))
        self._var_initial = tk.BooleanVar(value=self.cfg.get("include_person_initial", True))
        self._var_letter  = tk.StringVar(value=self.cfg.get("person_initial", "V"))
        self._var_slots   = tk.StringVar(value=str(self.cfg.get("slots_per_day", 6)))
        self._var_thresh  = tk.StringVar(value=str(self.cfg.get("hash_threshold", 5)))

        self._setup_styles()
        self._build_ui()

        # Traces depois do build para que _lbl_preview ja exista
        self._var_counter.trace_add("write", self._update_preview)
        self._var_initial.trace_add("write", self._on_initial_var_change)
        self._var_letter.trace_add("write", self._update_preview)

        self._update_preview()
        self._refresh_db_folder_label()
        self._reload_history_panel()

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

        # Barra de abas
        tab_bar = tk.Frame(self, bg=PANEL)
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

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Paginas de conteudo
        for key, build_fn in [
            ("main",     self._build_main_tab),
            ("settings", self._build_settings_tab),
        ]:
            page = tk.Frame(self, bg=BG)
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

        # Card: LOGs
        outer4, card4 = self._make_card(page, "LOGs")
        outer4.pack(fill="both", expand=True, **PAD)
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

        # Historico — cabecalho
        hist_hdr = tk.Frame(page, bg=BG)
        hist_hdr.pack(fill="x", padx=12, pady=(10, 2))
        tk.Label(
            hist_hdr, text="HISTÓRICO DE ENVIOS",
            font=FONT_LBL, bg=BG, fg=TXT_M, anchor="w",
        ).pack(side="left")
        self._btn(hist_hdr, "Resetar", self._reset_history, "danger_sm").pack(side="right")

        # Historico — canvas scrollavel
        hist_outer = tk.Frame(page, bg=BORDER, padx=1, pady=1)
        hist_outer.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        hist_card = tk.Frame(hist_outer, bg=PANEL)
        hist_card.pack(fill="both", expand=True)

        self._hist_canvas = tk.Canvas(
            hist_card, borderwidth=0, highlightthickness=0, height=160, bg=PANEL
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
                "activebackground": "#374151", "activeforeground": BPT,
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

    def set_step(self, step_index: int):
        self.progress["value"] = step_index
        self.lbl_status.config(text=STEPS[step_index])

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
            info, text=save_dt, anchor="w",
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

        url_row = tk.Frame(info, bg=PANEL)
        url_row.pack(fill="x", pady=(1, 0))
        url_short = (url[:68] + "...") if len(url) > 71 else url
        tk.Label(
            url_row, text=url_short,
            font=("Consolas", 7), fg=TXT_M, bg=PANEL, anchor="w",
        ).pack(side="left", fill="x", expand=True)
        tk.Button(
            url_row, image=self._ico_copy,
            relief="flat", bd=0, padx=2, pady=0,
            bg=PANEL, activebackground=INNER, cursor="hand2",
            command=lambda u=url: self._copy_to_clipboard(u),
        ).pack(side="right", padx=(4, 0))

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _reset_history(self):
        if not self._confirm_dialog(
            "Resetar Histórico",
            "Deseja realmente apagar todo o histórico de envios?\n\nEsta ação não pode ser desfeita.",
        ):
            return
        _save_history([])
        self._reload_history_panel()

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

        default_meta = {"views": "N/D", "likes": "N/D", "comments": "N/D"}
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

    def start_pipeline(self):
        link = self.entry_link.get().strip()
        if not link:
            self._show_result_popup(False, "Cole o link da publicação do Instagram antes de iniciar.")
            return
        db_folder = self.cfg.get("db_folder")
        if not db_folder or not Path(db_folder).is_dir():
            self._show_result_popup(False, "Selecione a pasta de análise antes de iniciar.")
            return
        self.btn_start.config(state="disabled")
        self.btn_paste_clear.config(state="disabled")
        self.progress["value"] = 0
        self.lbl_status.config(text=STEPS[0])
        self.clear_log()
        threading.Thread(
            target=self._run_pipeline, args=(link, Path(db_folder)), daemon=True
        ).start()

    def _run_pipeline(self, link: str, db_folder: Path):
        tmp_dir = Path(tempfile.mkdtemp(prefix="instabot_"))
        try:
            self._step(0, "Verificando configuracoes...")
            initial     = self.cfg.get("person_initial", "V")
            slots       = self.cfg.get("slots_per_day", 6)
            threshold   = self.cfg.get("hash_threshold", 5)
            inc_counter = self.cfg.get("include_day_counter", True)
            inc_initial = self.cfg.get("include_person_initial", True)

            self._step(1, "Preparando pasta do dia...")
            day_folder = organizer.ensure_day_folder(
                db_folder, initial, slots, inc_counter, inc_initial
            )
            slot = organizer.find_next_empty_slot(day_folder, slots)
            if slot is None:
                raise RuntimeError(
                    f"Todos os {slots} envios de hoje ja foram preenchidos em '{day_folder.name}'."
                )

            self._step(2, "Baixando midias do snapinsta.to...")
            media_paths, ig_meta = downloader.download_carousel(
                link, tmp_dir, progress_cb=lambda m: self._log_async(m)
            )

            self._step(3, "Verificando repeticoes...")
            post_index = dedup.build_post_index(db_folder)
            new_hashes = dedup.hash_new_media(media_paths)
            duplicate  = dedup.find_duplicate_post(new_hashes, post_index, threshold)
            if duplicate:
                existing_folder, max_dist = duplicate
                raise RuntimeError(
                    f"Publicacao repetida detectada!\n"
                    f"As primeiras imagens sao identicas as de:\n"
                    f"'{existing_folder.relative_to(db_folder)}'\n"
                    f"(distancia maxima: {max_dist})"
                )

            self._step(4, "Salvando arquivos na pasta de envio...")
            organizer.save_media_to_slot(slot, media_paths)

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

    def _step(self, index: int, text: str):
        self.after(0, lambda: (self.set_step(index), self._log_numbered(text)))

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


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
