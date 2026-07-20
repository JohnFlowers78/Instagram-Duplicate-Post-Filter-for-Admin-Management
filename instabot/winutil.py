"""Utilitarios de janela do Windows (via ctypes, sem dependencias externas).

Usado para mandar as janelas do navegador do robo (SnapInsta / Feed) para o
ULTIMO PLANO, deixando o app do Filtro na frente — sem fechar nem minimizar nada.
No-op fora do Windows (todas as funcoes degradam em silencio).
"""

import sys

_IS_WIN = sys.platform == "win32"

# Constantes do SetWindowPos
_HWND_BOTTOM = 1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_FLAGS = _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOACTIVATE


def send_chrome_windows_to_back() -> int:
    """Empurra para o fundo toda janela de topo cujo titulo termina em
    'Google Chrome' (o navegador do robo). Retorna quantas moveu.

    So mexe em Chrome — o app do Filtro (janela Tkinter) nao e afetado. Como so
    e chamado durante as operacoes do robo (coleta do Feed / download SnapInsta),
    o efeito colateral em um Chrome pessoal aberto e momentaneo e inofensivo.
    """
    if not _IS_WIN:
        return 0
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return 0

    user32 = ctypes.windll.user32
    moved = [0]

    proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            n = user32.GetWindowTextLengthW(hwnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value.endswith("Google Chrome"):
                user32.SetWindowPos(hwnd, _HWND_BOTTOM, 0, 0, 0, 0, _FLAGS)
                moved[0] += 1
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(proc_type(_cb), 0)
    except Exception:
        pass
    return moved[0]
