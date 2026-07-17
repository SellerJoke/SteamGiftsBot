:: 设置控制台编码为UTF-8且不显示本条命令
chcp 65001 >nul
:: 禁用命令回显
@echo off
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