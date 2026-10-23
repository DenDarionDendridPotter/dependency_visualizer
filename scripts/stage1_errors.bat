@echo off
cd /d "%~dp0\.."
chcp 65001 >nul
REM Демонстрация обработки ошибок для всех параметров конфигурации.

echo === корректная конфигурация config.xml
call .\run.bat --config config.xml
echo.
echo === файл конфигурации не существует
call .\run.bat --config configs\no_such_config.xml
for %%F in (configs\errors\*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
