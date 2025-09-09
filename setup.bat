@echo off
echo 正在设置Python项目环境...

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.6+
    pause
    exit /b 1
)

REM 创建虚拟环境（如果不存在）
if not exist ".venv\Scripts\activate.bat" (
    echo 创建虚拟环境...
    python -m venv .venv
    echo 虚拟环境创建成功
)

REM 激活虚拟环境
echo 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 升级pip
echo 升级pip...
python -m pip install --upgrade pip

REM 检查requirements.txt是否存在
if not exist "requirements.txt" (
    echo 错误: 未找到requirements.txt文件
    pause
    exit /b 1
)

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 依赖安装失败
    pause
    exit /b 1
)

echo 环境设置完成!
echo 请手动运行: .venv\Scripts\activate.bat 来激活虚拟环境
pause