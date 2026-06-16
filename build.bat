@echo off
chcp 65001 > nul
echo ============================================================
echo   Filtro de Repetidas - Gerar Executavel (PyInstaller)
echo ============================================================
echo.

echo [1/3] Verificando PyInstaller no venv...
instabot\venv\Scripts\pip.exe install pyinstaller --quiet
if errorlevel 1 (
    echo ERRO: nao foi possivel instalar o PyInstaller.
    pause & exit /b 1
)

echo.
echo [2/3] Gerando executavel...
instabot\venv\Scripts\python.exe -m PyInstaller filtro.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERRO: build falhou. Veja as mensagens acima.
    pause & exit /b 1
)

echo.
echo [3/3] Pronto!
echo.
echo  Executavel gerado em:
echo    dist\FiltroDeRepetidas\FiltroDeRepetidas.exe
echo.
echo  Para distribuir: zipar a pasta "dist\FiltroDeRepetidas\" inteira.
echo  (NAO incluir a subpasta "data\" - cada usuario cria a sua)
echo.
echo  Requisito na maquina de destino: Google Chrome instalado.
echo.
pause
