@echo off
cd /d "%~dp0\.."
chcp 65001 >nul
REM Вывод прямых зависимостей разных пакетов и ошибок загрузки.

echo === config.xml (пакет curl)
call .\run.bat --config config.xml
for %%F in (configs\stage2\*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
