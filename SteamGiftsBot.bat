:: 禁用命令回显
@echo off
:: 设置控制台编码为UTF-8且不显示本条命令
chcp 65001 >nul
:: 增加控制台缓冲区，减小由于最小化窗口后输出缓冲区满导致应用卡住的可能性
mode con: lines=9999
:: 检测 Python 是否安装且在 PATH 中可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未检测到Python，本应用依赖Python运行，请安装Python并将其添加到系统Path环境变量
    echo 访问 https://www.python.org/downloads/ 下载Python
    echo 访问 https://zhuanlan.zhihu.com/p/1969557833444992216 了解如何安装Python和配置Path环境变量
    pause
    exit /b 1
)
:: 如果虚拟环境不存在，则创建虚拟环境
if not exist .venv\Scripts\activate (
    echo "首次运行，创建运行环境中，请稍等..."
    python -m venv .venv
)
:: 激活虚拟环境并返回控制权
call .venv\Scripts\activate
:: 安装Python依赖（如果未安装）
pip install -q -r requirements.txt
:: 运行主程序
python -m src.main
pause