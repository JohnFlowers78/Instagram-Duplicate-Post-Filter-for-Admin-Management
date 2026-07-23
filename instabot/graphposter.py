"""Publicação no Instagram via API Graph da Meta (a estratégia "Método Seguro").

É a via OFICIAL (menor risco de ban): publica pela API autorizada, sem automação de
tela. Em troca, tem LIMITAÇÕES que valem lembrar:
  • SEM música (a API não adiciona faixas licenciadas/"em alta").
  • SEM agendamento nativo pela API → o AGENDAMENTO é feito pelo NOSSO vigia 24h
    (postplan diz a hora; quando chega, este módulo PUBLICA na hora).
  • Limite ~25 publicações/24h por conta.
  • Precisa de conta Instagram PROFISSIONAL (Business/Creator) vinculada a uma Página
    do Facebook, um app no Meta for Developers e um token de acesso.

⚠️ REQUISITO DE HOSPEDAGEM (importante): a API Graph NÃO aceita upload de arquivo local —
ela exige `image_url` PÚBLICO (cada imagem precisa estar acessível por URL https). Ou seja,
antes de publicar, as imagens do carrossel precisam ser hospedadas em algum lugar público
(servidor próprio, bucket, host temporário). Isso é `host_images()` — deixado plugável
porque depende da infraestrutura que o usuário escolher.

Fluxo da API (carrossel):
  1) para cada imagem: cria um "item container" (POST /media, is_carousel_item=true)
  2) cria o container do CARROSSEL (media_type=CAROUSEL, children=[...], caption)
  3) aguarda o container ficar FINISHED (processamento é assíncrono)
  4) publica (POST /media_publish, creation_id)
"""

import functools
import http.server
import json
import re
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import requests

from paths import DATA_DIR

GRAPH_VERSION = "v21.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
CONFIG_FILE = DATA_DIR / "graph_config.json"   # {"ig_user_id": "...", "access_token": "..."}
DAILY_LIMIT = 25                               # publicações/24h por conta (limite da Meta)


# --- configuração / credenciais --------------------------------------------
def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(ig_user_id: str, access_token: str) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(
        {"ig_user_id": ig_user_id.strip(), "access_token": access_token.strip()},
        ensure_ascii=False, indent=2), encoding="utf-8")


def is_configured(cfg: dict = None) -> bool:
    cfg = cfg or load_config()
    return bool(cfg.get("ig_user_id") and cfg.get("access_token"))


# --- infra HTTP -------------------------------------------------------------
class GraphError(RuntimeError):
    pass


def _post(cfg: dict, path: str, params: dict, timeout=60) -> dict:
    params = dict(params or {})
    params["access_token"] = cfg["access_token"]
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=timeout)
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        msg = (data.get("error") or {}).get("message", r.text)
        raise GraphError(f"{r.status_code}: {msg}")
    return data


def _get(cfg: dict, path: str, params: dict, timeout=60) -> dict:
    params = dict(params or {})
    params["access_token"] = cfg["access_token"]
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=timeout)
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        msg = (data.get("error") or {}).get("message", r.text)
        raise GraphError(f"{r.status_code}: {msg}")
    return data


def check_token(cfg: dict = None) -> dict:
    """Valida as credenciais lendo o próprio usuário IG. Retorna {'ok', 'username'|'error'}."""
    cfg = cfg or load_config()
    if not is_configured(cfg):
        return {"ok": False, "error": "credenciais ausentes"}
    try:
        me = _get(cfg, cfg["ig_user_id"], {"fields": "username"})
        return {"ok": True, "username": me.get("username", "")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# --- hospedagem por TÚNEL LOCAL TEMPORÁRIO (cloudflared) --------------------
# As imagens NÃO ficam em terceiros: sobe um mini-servidor local + um túnel efêmero
# (cloudflared quick tunnel) só durante a publicação; ao terminar, tudo é derrubado.
def cloudflared_path() -> str:
    """Acha o cloudflared: no PATH, ou baixado em %LOCALAPPDATA%\\cloudflared."""
    exe = shutil.which("cloudflared")
    if exe:
        return exe
    local = Path(DATA_DIR).parent / "cloudflared" / "cloudflared.exe"
    return str(local) if local.exists() else "cloudflared"


def cloudflared_installed() -> bool:
    return shutil.which("cloudflared") is not None or \
        (Path(DATA_DIR).parent / "cloudflared" / "cloudflared.exe").exists()


class TunnelHost:
    """Serve as imagens do carrossel por um túnel público efêmero (trycloudflare).
    Uso: host.start(paths) → lista de URLs https; host.stop() no fim (sempre)."""

    _URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def __init__(self, cloudflared: str = None):
        self.cloudflared = cloudflared or cloudflared_path()
        self._httpd = None
        self._thread = None
        self._proc = None
        self._tmp = None

    def start(self, local_paths, timeout_s: int = 40, report=None) -> list:
        paths = [Path(p) for p in local_paths]
        self._tmp = Path(tempfile.mkdtemp(prefix="graphpost_"))
        names = []
        for i, p in enumerate(paths, 1):
            name = f"{i:02d}{p.suffix.lower()}"      # 01.jpg, 02.jpg… (ordem garantida)
            shutil.copy(p, self._tmp / name)
            names.append(name)
        # mini-servidor local numa porta livre
        handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                    directory=str(self._tmp))
        self._httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
        port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        # túnel efêmero
        if report:
            report("• abrindo túnel cloudflared…")
        self._proc = subprocess.Popen(
            [self.cloudflared, "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        public = None
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            line = self._proc.stdout.readline()
            if not line:
                if self._proc.poll() is not None:
                    break
                continue
            m = self._URL_RE.search(line)
            if m:
                public = m.group(0)
                break
        if not public:
            self.stop()
            raise GraphError("não consegui abrir o túnel cloudflared (URL não apareceu)")
        if report:
            report(f"• túnel ativo: {public}")
        return [f"{public}/{n}" for n in names]

    def stop(self):
        for closer in (
            lambda: self._proc and self._proc.terminate(),
            lambda: self._httpd and self._httpd.shutdown(),
            lambda: self._httpd and self._httpd.server_close(),
            lambda: self._tmp and shutil.rmtree(self._tmp, ignore_errors=True),
        ):
            try:
                closer()
            except Exception:
                pass
        self._proc = self._httpd = self._thread = self._tmp = None


# --- containers / publicação -----------------------------------------------
def _create_item_container(cfg, image_url) -> str:
    d = _post(cfg, f"{cfg['ig_user_id']}/media",
              {"image_url": image_url, "is_carousel_item": "true"})
    return d["id"]


def _create_carousel_container(cfg, children_ids, caption) -> str:
    d = _post(cfg, f"{cfg['ig_user_id']}/media",
              {"media_type": "CAROUSEL", "children": ",".join(children_ids),
               "caption": caption or ""})
    return d["id"]


def _create_single_container(cfg, image_url, caption) -> str:
    d = _post(cfg, f"{cfg['ig_user_id']}/media",
              {"image_url": image_url, "caption": caption or ""})
    return d["id"]


def _wait_finished(cfg, container_id, timeout_s=120, report=None) -> bool:
    """Containers são processados de forma ASSÍNCRONA — esperar status FINISHED."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        st = _get(cfg, container_id, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return True
        if st == "ERROR":
            return False
        if report:
            report(f"  processando container… ({st})")
        time.sleep(4)
    return False


def _publish(cfg, creation_id) -> str:
    d = _post(cfg, f"{cfg['ig_user_id']}/media_publish", {"creation_id": creation_id})
    return d["id"]


def publish_carousel(image_urls, caption="", cfg=None, report=None) -> dict:
    """Publica AGORA um carrossel a partir de URLs públicas. Retorna {'ok','media_id','error'}.
    (O 'quando' é do vigia 24h; este módulo só executa a publicação no momento chamado.)"""
    r = {"ok": False, "media_id": "", "error": ""}
    cfg = cfg or load_config()
    if not is_configured(cfg):
        r["error"] = "API Graph não configurada (ig_user_id/access_token)"
        return r
    urls = list(image_urls or [])
    if not urls:
        r["error"] = "sem imagens"
        return r

    def log(m):
        if report:
            try:
                report(m)
            except Exception:
                pass

    try:
        if len(urls) == 1:
            log("• criando container (imagem única)…")
            creation_id = _create_single_container(cfg, urls[0], caption)
        else:
            children = []
            for i, u in enumerate(urls, 1):
                log(f"• criando item {i}/{len(urls)}…")
                cid = _create_item_container(cfg, u)
                if not _wait_finished(cfg, cid, report=report):
                    r["error"] = f"item {i} falhou no processamento"
                    return r
                children.append(cid)
            log("• criando container do carrossel…")
            creation_id = _create_carousel_container(cfg, children, caption)
        if not _wait_finished(cfg, creation_id, report=report):
            r["error"] = "container do carrossel não ficou pronto (FINISHED)"
            return r
        log("• publicando…")
        r["media_id"] = _publish(cfg, creation_id)
        r["ok"] = True
        log(f"✅ publicado (media_id={r['media_id']})")
    except Exception as exc:
        r["error"] = str(exc)
        log(f"ERRO: {exc}")
    return r


def publish_local_carousel(local_paths, caption="", cfg=None, report=None) -> dict:
    """Publica imagens LOCAIS: sobe um túnel efêmero (cloudflared), publica via API e
    derruba o túnel no fim (as imagens não ficam hospedadas em terceiros)."""
    if not cloudflared_installed():
        return {"ok": False, "media_id": "", "error":
                "cloudflared não instalado (necessário para o túnel de imagens)"}
    host = TunnelHost()
    try:
        urls = host.start(local_paths, report=report)
        return publish_carousel(urls, caption, cfg=cfg, report=report)
    except Exception as exc:
        return {"ok": False, "media_id": "", "error": str(exc)}
    finally:
        host.stop()
