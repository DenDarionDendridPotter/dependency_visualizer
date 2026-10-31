@echo off
cd /d "%~dp0\.."
chcp 65001 >nul
REM Построение графа зависимостей: тестовые репозитории, ошибки, Alpine.

echo ##### тестовый репозиторий: разные формы графа, глубина, фильтр
for %%F in (configs\stage3\tree_*.xml configs\stage3\diamond*.xml configs\stage3\wide*.xml configs\stage3\chain_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
echo.
echo ##### тестовый репозиторий: циклические зависимости
for %%F in (configs\stage3\cycle*.xml configs\stage3\self_loop.xml configs\stage3\two_cycles.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
echo.
echo ##### ошибки
for %%F in (configs\stage3\error_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
echo.
echo ##### настоящий репозиторий Alpine (нужен интернет)
for %%F in (configs\stage3\real_*.xml) do (
    echo.
    echo === %%F
    call .\run.bat --config %%F
)
