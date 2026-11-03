@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo ===== K-Sori 설치 =====
where python >nul 2>nul || (echo [!] 파이썬이 없어요. https://www.python.org 에서 3.10 이상을 설치하고 "Add to PATH"를 꼭 체크하세요. & pause & exit /b 1)
if not exist venv (
  echo [1/3] 가상환경 만드는 중...
  python -m venv venv || (echo [!] 가상환경을 못 만들었어요 & pause & exit /b 1)
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo [2/3] 그래픽카드용 torch 설치 중... (몇 분 걸려요)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126 || (echo [!] torch 설치 실패 & pause & exit /b 1)
echo [3/3] 나머지 설치 중...
pip install -r requirements.txt || (echo [!] 설치 실패 & pause & exit /b 1)
python -c "import torch;print('그래픽카드 사용:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
echo.
echo ===== 설치 끝 =====
echo 다음: README.md 의 "처음 해 보기" 를 따라 하세요.
pause
