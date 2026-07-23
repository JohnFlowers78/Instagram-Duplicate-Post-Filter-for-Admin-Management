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

import json
import time

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


# --- hospedagem das imagens (PLUGÁVEL) --------------------------------------
def host_images(local_paths) -> list:
    """Transforma caminhos LOCAIS em URLs PÚBLICAS (https) — exigência da API Graph.
    A implementação depende da infra escolhida pelo usuário (servidor/bucket/host
    temporário). Enquanto não definida, levanta erro claro."""
    raise NotImplementedError(
        "host_images() não configurado: a API Graph exige image_url público. "
        "Defina onde hospedar as imagens (servidor próprio, bucket S3/GCS, etc.).")


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
    """Conveniência: hospeda as imagens locais (host_images) e publica.
    Só funciona quando host_images() estiver configurado."""
    urls = host_images(local_paths)
    return publish_carousel(urls, caption, cfg=cfg, report=report)
