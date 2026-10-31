@echo off
cd /d "%~dp0\.."
chcp 65001 >nul
REM Описание графа на языке Mermaid и ASCII-дерево.

echo ##### тестовый репозиторий: цикл, глубина, ромб, обратные зависимости
for %%F in (configs\stage5\test_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
echo.
echo ##### три пакета настоящего репозитория Alpine (нужен интернет)
for %%F in (configs\stage5\real_curl.xml configs\stage5\real_bash.xml configs\stage5\real_git.xml configs\stage5\real_reverse_curl.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
