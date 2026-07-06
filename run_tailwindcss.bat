@echo off
setlocal
cd /d %~dp0

:: 実行ファイル名の設定
set EXE_NAME=tailwindcss-windows-x64.exe

:: ファイルが存在するかチェック
if not exist "%EXE_NAME%" (
    echo ======================================================
    echo [エラー] %EXE_NAME% が見つかりません。
    echo.
    echo 以下のGitHubページから最新の Windows 用バイナリを
    echo ダウンロードして、このフォルダに配置してください。
    echo https://github.com/tailwindlabs/tailwindcss/releases
    echo ======================================================
    pause
    exit /b
)

:: ファイルがある場合は実行
echo Tailwind CSS を監視中...
.\%EXE_NAME% -i ./src/input.css -o ./static/css/tailwind.css --watch