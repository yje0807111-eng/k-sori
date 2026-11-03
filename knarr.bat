@echo off
rem 사용 예: knarr.bat narrate 대본.txt   (이 폴더의 설정.json 을 씀. 다른 설정은 끝에 -c 다른설정.json)
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
call venv\Scripts\activate.bat
if exist 설정.json (
  python -m knarr -c 설정.json %*
) else (
  python -m knarr %*
)
