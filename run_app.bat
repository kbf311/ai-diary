@echo off
cd /d %~dp0

:: 1. 仮想環境を有効化
call venv\Scripts\activate

:: 2. ブラウザでURLを開く（先に実行）
start http://localhost:5000

:: 3. Python スクリプトを実行
python app.py

pause