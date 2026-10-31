@echo off
cd /d "%~dp0\.."
chcp 65001 >nul
REM Обратные зависимости: кто зависит от пакета.

echo ##### тестовый репозиторий: обратные зависимости
for %%F in (configs\stage4\reverse_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
echo.
echo ##### ошибки
for %%F in (configs\stage4\error_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
echo.
echo === configs\errors\bad_reverse.xml
call .\run.bat --config configs\errors\bad_reverse.xml
echo.
echo ##### настоящий репозиторий Alpine (нужен интернет)
for %%F in (configs\stage4\real_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
