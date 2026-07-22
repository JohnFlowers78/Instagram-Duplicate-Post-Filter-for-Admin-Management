"""Vínculo do ambiente Android (AVD) ao projeto — camada fina sobre o ADB.

Localiza o SDK/adb/emulador instalados e oferece helpers para o poster:
ligar/desligar o emulador, esperar boot, enviar imagens (adb push), etc.

Instalação SEM admin (padrão): SDK em %LOCALAPPDATA%\\Android\\Sdk, JDK em
%LOCALAPPDATA%\\Android\\jdk17, AVD "postador" (Android 14, Play Store).

Degrada com elegância: se nada estiver instalado, is_installed()=False e a aba
de Postagem mostra "ambiente Android não configurado" (o resto do app roda 100%).
"""

import os
import subprocess
import time
from pathlib import Path

_LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
# SDK: env ANDROID_HOME/ANDROID_SDK_ROOT tem prioridade; senão o padrão sem-admin
SDK_ROOT = Path(os.environ.get("ANDROID_HOME")
                or os.environ.get("ANDROID_SDK_ROOT")
                or (_LOCAL / "Android" / "Sdk"))
JAVA_HOME = Path(os.environ.get("ANDROID_JDK") or (_LOCAL / "Android" / "jdk17"))
AVD_NAME = "postador"

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def adb_path() -> Path:
    return SDK_ROOT / "platform-tools" / "adb.exe"


def emulator_path() -> Path:
    return SDK_ROOT / "emulator" / "emulator.exe"


def is_installed() -> bool:
    return adb_path().exists() and emulator_path().exists()


def _run(args, timeout=30) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           timeout=timeout, creationflags=_NOWIN)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as exc:
        return f"ERRO: {exc}"


def devices() -> list:
    out = _run([str(adb_path()), "devices"])
    devs = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devs.append(parts[0])
    return devs


def emulator_running() -> bool:
    return any(d.startswith("emulator-") for d in devices())


def list_avds() -> list:
    if not emulator_path().exists():
        return []
    out = _run([str(emulator_path()), "-list-avds"])
    return [l.strip() for l in out.splitlines() if l.strip() and "ERRO" not in l]


def start_emulator(avd: str = AVD_NAME):
    """Liga o emulador (janela própria). Retorna o Popen ou None se indisponível."""
    if not emulator_path().exists():
        return None
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_ROOT)
    env["ANDROID_SDK_ROOT"] = str(SDK_ROOT)
    return subprocess.Popen(
        [str(emulator_path()), "-avd", avd, "-gpu", "auto", "-no-boot-anim"],
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def boot_completed() -> bool:
    return _run([str(adb_path()), "shell", "getprop", "sys.boot_completed"]).strip() == "1"


def wait_boot(timeout_s: int = 180) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if emulator_running() and boot_completed():
            return True
        time.sleep(3)
    return False


def ensure_running(timeout_s: int = 180) -> bool:
    """Garante o emulador ligado e bootado (liga se preciso)."""
    if emulator_running() and boot_completed():
        return True
    start_emulator()
    return wait_boot(timeout_s)


def stop_emulator() -> None:
    for d in devices():
        if d.startswith("emulator-"):
            _run([str(adb_path()), "-s", d, "emu", "kill"])


def app_installed(package: str) -> bool:
    out = _run([str(adb_path()), "shell", "pm", "list", "packages", package])
    return f"package:{package}" in out


def instagram_installed() -> bool:
    return app_installed("com.instagram.android")


def push_images(local_paths, remote_dir: str = "/sdcard/Pictures/postador") -> list:
    """Envia as imagens do carrossel para o emulador e reindexa a galeria."""
    _run([str(adb_path()), "shell", "mkdir", "-p", remote_dir])
    pushed = []
    for p in local_paths:
        out = _run([str(adb_path()), "push", str(p), remote_dir])
        if "error" not in out.lower():
            pushed.append(f"{remote_dir}/{Path(p).name}")
    _run([str(adb_path()), "shell", "am", "broadcast", "-a",
          "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_dir}"])
    return pushed


def env_summary() -> dict:
    return {
        "installed": is_installed(),
        "sdk": str(SDK_ROOT),
        "jdk": str(JAVA_HOME),
        "adb": str(adb_path()),
        "avds": list_avds(),
        "emulator_running": emulator_running() if adb_path().exists() else False,
        "instagram_installed": instagram_installed() if adb_path().exists() else False,
    }
