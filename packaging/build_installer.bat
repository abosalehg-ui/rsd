@echo off
REM ╔══════════════════════════════════════════════════════════════╗
REM ║  رصد (Rasad) — بناء مثبّت ويندوز كامل (PyInstaller + Inno Setup) ║
REM ╚══════════════════════════════════════════════════════════════╝
REM شغّل هذا الملف من أي مكان (ينتقل تلقائياً لجذر المستودع).
REM المتطلّبات: Python 3.10+، Node.js 18+، و Inno Setup 6 (ISCC في PATH).

setlocal enabledelayedexpansion
cd /d "%~dp0\.."
echo === جذر المستودع: %cd% ===

echo.
echo [1/4] بناء الواجهة (Vite)...
pushd frontend
call npm ci || goto :err
call npm run build || goto :err
popd

echo.
echo [2/4] تجهيز بيئة بايثون + PyInstaller...
pushd backend
pip install -r requirements.txt || goto :err
popd
pip install pyinstaller || goto :err

echo.
echo [3/4] تجميع التطبيق (PyInstaller onedir)...
pyinstaller packaging\rasad.spec --noconfirm --clean || goto :err

echo.
echo [4/4] بناء المثبّت (Inno Setup)...
where ISCC >nul 2>nul
if errorlevel 1 (
  echo.
  echo [!] لم يُعثر على ISCC.exe في PATH.
  echo     ثبّت Inno Setup 6 من https://jrsoftware.org/isdl.php
  echo     ثم أضف مجلّده ^(مثل "C:\Program Files ^(x86^)\Inno Setup 6"^) إلى PATH.
  echo     أو صرّف يدوياً: افتح packaging\rasad.iss في Inno Setup واضغط Compile.
  goto :err
)
ISCC packaging\rasad.iss || goto :err

echo.
echo ============================================================
echo  تم بنجاح! المثبّت في:  packaging\Output\Rasad-Setup-x64.exe
echo ============================================================
goto :eof

:err
echo.
echo [X] فشل البناء — راجع الرسائل أعلاه.
exit /b 1
