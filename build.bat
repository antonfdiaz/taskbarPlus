@echo off

echo building taskbarPlus...
pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found!
    popd
    pause
    exit /b 1
)

set "NUITKA_CACHE_DIR=%CD%\.nuitka-cache"

".venv\Scripts\python.exe" -m nuitka main.py --onefile --plugin-enable=pyside6 --assume-yes-for-downloads --windows-console-mode=disable --output-filename=taskbarPlus --windows-icon-from-ico=assets/icon.png
if errorlevel 1 (
    echo build failed!
    popd
    pause
    exit /b 1
)

popd
echo build complete!
pause