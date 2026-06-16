@echo off

echo building taskbarPlus (dev)...
title taskbarPlus (dev) build
pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found!
    popd
    pause
    exit /b 1
)

set "NUITKA_CACHE_DIR=%CD%\.nuitka-cache"

".venv\Scripts\python.exe" -m nuitka main.py ^
  --standalone ^
  --plugin-enable=pyside6 ^
  --assume-yes-for-downloads ^
  --output-filename=taskbarPlus-dev ^
  --windows-icon-from-ico=assets/icon.png

if errorlevel 1 (
    echo build failed!
    popd
    pause
    exit /b 1
)

popd
echo build complete!
pause