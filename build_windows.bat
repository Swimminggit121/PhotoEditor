@echo off
setlocal

cd /d "%~dp0"

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is missing. Install the build dependencies with:
    echo     python -m pip install -r requirements-build.txt
    exit /b 1
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --collect-all imageio_ffmpeg ^
    --collect-all keyring ^
    --name PhotoEditor-Suite ^
    main.py

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

copy /Y "dist\PhotoEditor-Suite.exe" "dist\PhotoEditor-Photo.exe" >nul
if errorlevel 1 exit /b 1
copy /Y "dist\PhotoEditor-Suite.exe" "dist\PhotoEditor-Video.exe" >nul
if errorlevel 1 exit /b 1

python -c "from pathlib import Path; files=[Path('dist')/('PhotoEditor-'+edition+'.exe') for edition in ('Photo','Video','Suite')]; [print(f'{path}: {path.stat().st_size:,} bytes') for path in files]; raise SystemExit(any(path.stat().st_size > 16*1024**3 for path in files))"
if errorlevel 1 (
    echo An executable exceeded the 16 GiB size limit or could not be verified.
    exit /b 1
)

echo.
echo Build complete:
echo   dist\PhotoEditor-Photo.exe  ^(photo workspace^)
echo   dist\PhotoEditor-Video.exe  ^(video workspace^)
echo   dist\PhotoEditor-Suite.exe  ^(photo and video workspace chooser^)
