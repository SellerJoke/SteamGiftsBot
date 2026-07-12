@echo off
chcp 65001
if not exist .venv\Scripts\activate (
    echo "首次运行，创建虚拟环境，需要的时间较长，请稍等..."
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -q -r requirements.txt
python -m src.main
pause