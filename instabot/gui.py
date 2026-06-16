import json
import re
import shutil
import tempfile
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

import requests
from PIL import Image, ImageDraw, ImageTk

import config
import dedup
import downloader
import organizer

HISTORY_FILE = Path(__file__).parent / "data" / "history.json"
THUMB_SIZE = (64, 64)
ICON_PX = 13  # tamanho dos icones de metadado em pixels

STEPS = [
    "Verificando configuracoes...",
    "Preparando pasta do dia...",
    "Baixando midias do snapinsta.to...",
    "Verificando repeticoes...",
    "Salvando arquivos na pasta de envio...",
    "Concluido!",
]


# ---------------------------------------------------------------------------
# Criacao de icones com PIL
# ---------------------------------------------------------------------------

def _make_icon(draw_fn, size: int = ICON_PX) -> ImageTk.PhotoImage:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(img), size)
    return ImageTk.PhotoImage(img)


def _icon_eye(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (80, 80, 80, 255)
        # forma de olho: elipse horizontal
        d.arc([0, s // 4, s - 1, s * 3 // 4 - 1], start=180, end=360, fill=c, width=1)
        d.arc([0, s // 4, s - 1, s * 3 // 4 - 1], start=0, end=180, fill=c, width=1)
        # pupila
        r = max(1, s // 6)
        cx, cy = s // 2, s // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return _make_icon(draw, size)


def _icon_heart(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (80, 80, 80, 255)
        h = s // 2
        # dois arcos superiores
        d.arc([0, 0, h, h], start=180, end=360, fill=c, width=1)
        d.arc([h - 2, 0, s - 1, h], start=180, end=360, fill=c, width=1)
        # lados descendo ate o ponto inferior
        q = h // 2
        d.line([(0, q), (s // 2, s - 1)], fill=c, width=1)
        d.line([(s - 1, q), (s // 2, s - 1)], fill=c, width=1)
    return _make_icon(draw, size)


def _icon_bubble(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (80, 80, 80, 255)
        tail = max(2, s // 4)
        d.ellipse([0, 0, s - 1, s - 1 - tail], outline=c, width=1)
        d.polygon([(1, s - tail - 1), (0, s - 1), (tail + 1, s - tail - 1)], fill=c)
    return _make_icon(draw, size)


def _icon_copy(size: int = ICON_PX) -> ImageTk.PhotoImage:
    def draw(d, s):
        c = (80, 80, 80, 255)
        off = s // 4
        d.rectangle([off, 0, s - 1, s - 1 - off], outline=c, width=1)
        d.rectangle([0, off, s - 1 - off, s - 1], outline=c, width=1)
    return _make_icon(draw, size)


# ---------------------------------------------------------------------------
# Metadados do Instagram (best-effort)
# ---------------------------------------------------------------------------

def _try_fetch_ig_meta(url: str) -> dict:
    """Tenta obter views, likes e comentarios de um post publico. Fallback N/D."""
    meta = {"views": "N/D", "likes": "N/D", "comments": "N/D"}

    sc_m = re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)", url)
    if not sc_m:
        return meta
    shortcode = sc_m.group(1)

    hdrs = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Referer": "https://www.instagram.com/",
    }

    def _parse_media(sm: dict):
        if sm.get("edge_media_preview_like", {}).get("count") is not None:
            meta["likes"] = str(sm["edge_media_preview_like"]["count"])
        if sm.get("edge_media_to_comment", {}).get("count") is not None:
            meta["comments"] = str(sm["edge_media_to_comment"]["count"])
        if sm.get("video_view_count") is not None:
            meta["views"] = str(sm["video_view_count"])

    # Tentativa 1: pagina de embed do Instagram (geralmente tem dados estruturados)
    try:
        r = requests.get(
            f"https://www.instagram.com/p/{shortcode}/embed/captioned/",
            headers=hdrs,
            timeout=10,
        )
        if r.ok:
            text = r.text
            # window.__additionalDataLoaded contem dados do post
            dm = re.search(
                r"window\.__additionalDataLoaded\s*\(\s*'[^']*'\s*,\s*(\{.+?\})\s*\)\s*;",
                text,
                re.DOTALL,
            )
            if dm:
                data = json.loads(dm.group(1))
                _parse_media(data.get("shortcode_media", {}))
            # Fallback: JSON embutido em tag <script type="application/json">
            if meta["likes"] == "N/D":
                for sm_m in re.finditer(
                    r'<script type="application/json"[^>]*>(\{.+?\})</script>',
                    text,
                    re.DOTALL,
                ):
                    try:
                        d = json.loads(sm_m.group(1))
                        if "shortcode_media" in d:
                            _parse_media(d["shortcode_media"])
                            break
                    except Exception:
                        pass
            if meta["likes"] != "N/D" or meta["comments"] != "N/D":
                return meta
    except Exception:
        pass

    # Tentativa 2: oEmbed
    try:
        r = requests.get(
            f"https://api.instagram.com/oembed/?url={url}&omitscript=true",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        if r.ok:
            title = r.json().get("title", "")
            lm = re.search(r"([\d,\.]+)\s+(?:Likes?|curtidas?)", title, re.I)
            if lm:
                meta["likes"] = lm.group(1)
            cm = re.search(r"([\d,\.]+)\s+(?:Comments?|coment[aá]rios?)", title, re.I)
            if cm:
                meta["comments"] = cm.group(1)
            if meta["likes"] != "N/D" or meta["comments"] != "N/D":
                return meta
    except Exception:
        pass

    # Tentativa 3: JSON-LD na pagina do post
    try:
        r = requests.get(url, headers=hdrs, timeout=10)
        if r.ok:
            m = re.search(
                r'<script type="application/ld\+json">(.+?)</script>', r.text, re.DOTALL
            )
            if m:
                data = json.loads(m.group(1))
                for stat in data.get("interactionStatistic", []):
                    itype = stat.get("interactionType", "")
                    count = stat.get("userInteractionCount")
                    if count is not None:
                        if "LikeAction" in itype:
                            meta["likes"] = str(count)
                        elif "CommentAction" in itype:
                            meta["comments"] = str(count)
    except Exception:
        pass

    return meta


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
        self.geometry("600x720")
        self.minsize(540, 520)
        self.resizable(True, True)

        self.cfg = config.load_config()
        self._thumb_refs: list = []
        self._result_popup = None
        self._log_counter = 0

        # Icones criados uma vez e reutilizados em todas as linhas do historico
        self._ico_eye = _icon_eye()
        self._ico_heart = _icon_heart()
        self._ico_bubble = _icon_bubble()
        self._ico_copy = _icon_copy()

        self._build_widgets()
        self._refresh_db_folder_label()
        self._reload_history_panel()

    # ------------------------------------------------------------------
    # Construcao da interface
    # ------------------------------------------------------------------
    def _build_widgets(self):
        pad = {"padx": 10, "pady": 4}

        # Pasta de historico
        frame_db = tk.LabelFrame(self, text="Pasta de analise (historico de envios)")
        frame_db.pack(fill="x", **pad)
        self.lbl_db_folder = tk.Label(
            frame_db, text="(nenhuma pasta selecionada)", anchor="w", wraplength=420
        )
        self.lbl_db_folder.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        tk.Button(frame_db, text="Selecionar pasta...", command=self.choose_db_folder).pack(
            side="right", padx=8, pady=6
        )

        # Link + Colar/Limpar + Iniciar
        frame_link = tk.LabelFrame(self, text="Nova publicacao do Instagram")
        frame_link.pack(fill="x", **pad)
        self.entry_link = tk.Entry(frame_link)
        self.entry_link.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self.entry_link.bind("<KeyRelease>", self._on_link_change)

        self.btn_paste_clear = tk.Button(
            frame_link, text="Colar", width=7, command=self._paste_or_clear
        )
        self.btn_paste_clear.pack(side="left", padx=(0, 4), pady=8)

        self.btn_start = tk.Button(
            frame_link, text="Iniciar", width=7, command=self.start_pipeline
        )
        self.btn_start.pack(side="left", padx=(0, 8), pady=8)

        # Progresso
        frame_prog = tk.LabelFrame(self, text="Progresso")
        frame_prog.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(
            frame_prog, orient="horizontal", mode="determinate", maximum=len(STEPS)
        )
        self.progress.pack(fill="x", padx=8, pady=(6, 2))
        self.lbl_status = tk.Label(frame_prog, text="Aguardando...", anchor="w")
        self.lbl_status.pack(fill="x", padx=8, pady=(0, 6))

        # Log
        frame_log = tk.LabelFrame(self, text="LOGs")
        frame_log.pack(fill="both", expand=True, **pad)
        sb_log = ttk.Scrollbar(frame_log, orient="vertical")
        self.txt_log = tk.Text(
            frame_log, height=5, state="disabled", wrap="word", yscrollcommand=sb_log.set
        )
        sb_log.config(command=self.txt_log.yview)
        self.txt_log.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb_log.pack(side="right", fill="y", pady=8, padx=(0, 8))

        # Cabecalho do historico
        hdr = tk.Frame(self)
        hdr.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(hdr, text="Historico de envios bem-sucedidos", font=("Arial", 9, "bold")).pack(
            side="left"
        )
        tk.Button(hdr, text="Resetar historico", command=self._reset_history).pack(side="right")

        # Painel de historico (Canvas scrollavel)
        frame_hist = tk.Frame(self, bd=1, relief="sunken")
        frame_hist.pack(fill="both", expand=True, padx=10, pady=(2, 8))

        self._hist_canvas = tk.Canvas(frame_hist, borderwidth=0, highlightthickness=0, height=180)
        sb_hist = ttk.Scrollbar(frame_hist, orient="vertical", command=self._hist_canvas.yview)
        self._hist_canvas.configure(yscrollcommand=sb_hist.set)

        self._hist_inner = tk.Frame(self._hist_canvas)
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

    def _on_hist_scroll(self, event):
        self._hist_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
    # Helpers de UI
    # ------------------------------------------------------------------
    def _refresh_db_folder_label(self):
        folder = self.cfg.get("db_folder") or ""
        self.lbl_db_folder.config(text=folder if folder else "(nenhuma pasta selecionada)")

    def choose_db_folder(self):
        folder = filedialog.askdirectory(
            title="Selecione a pasta onde estao os envios anteriores"
        )
        if folder:
            self.cfg["db_folder"] = folder
            config.save_config(self.cfg)
            self._refresh_db_folder_label()

    def _log_numbered(self, msg: str):
        """Cabecalho numerado de cada etapa — [N] texto."""
        self._log_counter += 1
        self.txt_log.config(state="normal")
        if self._log_counter > 1:
            self.txt_log.insert("end", "\n")   # linha em branco entre etapas
        self.txt_log.insert("end", f"[{self._log_counter}] {msg}\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def log(self, msg: str):
        """Detalhe dentro da etapa atual — sem numero, recuado."""
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
    # Popup de resultado (clique em qualquer lugar do popup para fechar)
    # ------------------------------------------------------------------
    def _show_result_popup(self, success: bool, msg: str):
        self._close_result_popup()
        popup = tk.Toplevel(self)
        self._result_popup = popup
        popup.title("Sucesso" if success else "Erro")
        popup.resizable(False, False)
        popup.transient(self)
        popup.attributes("-topmost", True)

        bg = "#e8f5e9" if success else "#ffebee"
        fg = "#1b5e20" if success else "#b71c1c"
        icon = "✓" if success else "✗"
        popup.configure(bg=bg, cursor="hand2")

        tk.Label(
            popup,
            text=f"{icon}  {msg}",
            bg=bg, fg=fg,
            font=("Arial", 10),
            wraplength=380,
            padx=24, pady=16,
            justify="left",
        ).pack()
        tk.Label(
            popup,
            text="[ Clique em qualquer lugar aqui para fechar ]",
            bg=bg, fg="#aaa",
            font=("Arial", 8),
        ).pack(pady=(0, 12))

        def dismiss(event=None):
            self._close_result_popup()

        popup.bind("<Button-1>", dismiss)
        for child in popup.winfo_children():
            child.bind("<Button-1>", dismiss)

        # Clicar em qualquer lugar da janela principal tambem fecha o popup
        self.bind("<Button-1>", lambda e: dismiss())

        self.update_idletasks()
        w, h = 440, 140
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

    def _close_result_popup(self):
        if self._result_popup:
            try:
                self._result_popup.destroy()
            except Exception:
                pass
            self._result_popup = None
        try:
            self.unbind("<Button-1>")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Painel de historico
    # ------------------------------------------------------------------
    def _reload_history_panel(self):
        for w in self._hist_inner.winfo_children():
            w.destroy()
        self._thumb_refs.clear()
        entries = _load_history()
        if not entries:
            tk.Label(
                self._hist_inner,
                text="Nenhum envio registrado ainda.",
                fg="gray",
                font=("Arial", 9),
            ).pack(pady=12, padx=12)
            return
        for entry in entries:
            self._add_history_row(entry)

    def _add_history_row(self, entry: dict):
        row = tk.Frame(self._hist_inner, bd=1, relief="solid", padx=4, pady=4)
        row.pack(fill="x", padx=4, pady=2)

        # Miniatura
        thumb_frame = tk.Frame(row, width=THUMB_SIZE[0] + 4, height=THUMB_SIZE[1] + 4)
        thumb_frame.pack(side="left", padx=(0, 8))
        thumb_frame.pack_propagate(False)
        thumb_path = entry.get("thumbnail", "")
        loaded = False
        if thumb_path and Path(thumb_path).exists():
            try:
                img = Image.open(thumb_path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._thumb_refs.append(photo)
                tk.Label(thumb_frame, image=photo).pack(expand=True)
                loaded = True
            except Exception:
                pass
        if not loaded:
            tk.Label(
                thumb_frame, text="[sem\nimagem]", fg="gray", font=("Arial", 7), justify="center"
            ).pack(expand=True)

        # Informacoes textuais
        info = tk.Frame(row)
        info.pack(side="left", fill="x", expand=True)

        folder = entry.get("folder", "")
        save_dt = entry.get("save_datetime", "")
        url = entry.get("url", "")
        meta = entry.get("meta", {})

        tk.Label(info, text=f"Pasta: {folder}", anchor="w", font=("Arial", 9, "bold")).pack(
            fill="x"
        )
        tk.Label(info, text=f"Salvo em: {save_dt}", anchor="w", font=("Arial", 8)).pack(fill="x")

        # Linha de metricas com icones
        meta_frame = tk.Frame(info)
        meta_frame.pack(fill="x", pady=(1, 0))
        font8 = ("Arial", 8)

        for ico, key in [
            (self._ico_eye, "views"),
            (self._ico_heart, "likes"),
            (self._ico_bubble, "comments"),
        ]:
            tk.Label(meta_frame, image=ico).pack(side="left", padx=(0, 2))
            tk.Label(meta_frame, text=meta.get(key, "N/D"), font=font8, anchor="w").pack(
                side="left", padx=(0, 10)
            )

        # URL resumida + botao copiar
        url_frame = tk.Frame(info)
        url_frame.pack(fill="x", pady=(1, 0))
        url_short = (url[:68] + "...") if len(url) > 71 else url
        tk.Label(url_frame, text=url_short, font=("Arial", 7), fg="#aaa", anchor="w").pack(
            side="left", fill="x", expand=True
        )
        btn_copy = tk.Button(
            url_frame,
            image=self._ico_copy,
            relief="flat",
            padx=2, pady=0,
            cursor="hand2",
            command=lambda u=url: self._copy_to_clipboard(u),
        )
        btn_copy.pack(side="right", padx=(4, 0))

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _reset_history(self):
        _save_history([])
        for w in self._hist_inner.winfo_children():
            w.destroy()
        self._thumb_refs.clear()
        tk.Label(
            self._hist_inner,
            text="Nenhum envio registrado ainda.",
            fg="gray",
            font=("Arial", 9),
        ).pack(pady=12, padx=12)

    def _record_history(self, url: str, slot: Path):
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

        entry = {
            "url": url,
            "save_datetime": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "folder": folder_label,
            "thumbnail": thumb_path,
            "meta": {"views": "N/D", "likes": "N/D", "comments": "N/D"},
        }

        entries = _load_history()
        entries.insert(0, entry)
        _save_history(entries)
        self.after(0, self._reload_history_panel)

        # Busca metadados em segundo plano e atualiza
        def fetch_and_update():
            meta = _try_fetch_ig_meta(url)
            entry["meta"] = meta
            all_entries = _load_history()
            for e in all_entries:
                if e.get("url") == url and e.get("save_datetime") == entry["save_datetime"]:
                    e["meta"] = meta
                    break
            _save_history(all_entries)
            self.after(0, self._reload_history_panel)

        threading.Thread(target=fetch_and_update, daemon=True).start()

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def start_pipeline(self):
        link = self.entry_link.get().strip()
        if not link:
            self._show_result_popup(
                False, "Cole o link da publicacao do Instagram antes de iniciar."
            )
            return

        db_folder = self.cfg.get("db_folder")
        if not db_folder or not Path(db_folder).is_dir():
            self._show_result_popup(False, "Selecione a pasta de analise antes de iniciar.")
            return

        self.btn_start.config(state="disabled")
        self.btn_paste_clear.config(state="disabled")
        self.progress["value"] = 0
        self.lbl_status.config(text=STEPS[0])
        self.clear_log()  # limpa mensagens do processo anterior

        threading.Thread(
            target=self._run_pipeline, args=(link, Path(db_folder)), daemon=True
        ).start()

    def _run_pipeline(self, link: str, db_folder: Path):
        tmp_dir = Path(tempfile.mkdtemp(prefix="instabot_"))
        try:
            self._step(0, "Verificando configuracoes...")
            initial = self.cfg.get("person_initial", "V")
            slots = self.cfg.get("slots_per_day", 6)
            threshold = self.cfg.get("hash_threshold", 5)

            self._step(1, "Preparando pasta do dia...")
            day_folder = organizer.ensure_day_folder(db_folder, initial, slots)
            slot = organizer.find_next_empty_slot(day_folder, slots)
            if slot is None:
                raise RuntimeError(
                    f"Todos os {slots} envios de hoje ja foram preenchidos em '{day_folder.name}'."
                )

            self._step(2, "Baixando midias do snapinsta.to...")
            media_paths = downloader.download_carousel(
                link, tmp_dir, progress_cb=lambda m: self._log_async(m)
            )

            self._step(3, "Verificando repeticoes...")
            post_index = dedup.build_post_index(db_folder)
            new_hashes = dedup.hash_new_media(media_paths)
            duplicate = dedup.find_duplicate_post(new_hashes, post_index, threshold)
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
            self._done(True, f"Publicacao salva com sucesso!\n{slot_label}", link, slot)

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

    def _done(self, success: bool, msg: str, link: str = "", slot: Path | None = None):
        def finish():
            self.btn_start.config(state="normal")
            self.btn_paste_clear.config(state="normal")
            if success:
                self.entry_link.delete(0, "end")
                self.btn_paste_clear.config(text="Colar")
                if slot:
                    self._record_history(link, slot)
            else:
                self.progress["value"] = 0
                self.lbl_status.config(text="Erro - veja mensagens abaixo")
            self._show_result_popup(success, msg)

        self.after(0, finish)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
