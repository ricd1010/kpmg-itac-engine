@echo off
echo ======================================================
echo      KPMG ITAC Audit Workpaper Engine - Starter
echo ======================================================
echo.
echo 正在检查运行环境...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境，请先安装 Python 3.10+
    pause
    exit
)

echo 正在自动安装审计引擎依赖库 (仅第一次运行需联网)...
py -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo 正在启动毕马威 ITAC 自动化底稿中心...
echo 启动成功后，请在浏览器访问: http://localhost:8501
echo.
py -m streamlit run src/app.py

pause
