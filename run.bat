@echo off
echo 开始运行脚本...

REM 激活虚拟环境
echo 激活虚拟环境...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo 错误: 未找到虚拟环境，请先运行 setup.bat
    pause
    exit /b 1
)

echo 运行 get_datasets.py...
python get_datasets.py
if errorlevel 1 (
    echo get_datasets.py 执行失败，程序退出
    pause
    exit /b 1
)

echo 运行 get_tags.py...
python get_tags.py
if errorlevel 1 (
    echo get_tags.py 执行失败，程序退出
    pause
    exit /b 1
)

echo 运行 llm.py...
python llm.py
if errorlevel 1 (
    echo llm.py 执行失败，程序退出
    pause
    exit /b 1
)

echo 运行 tts.py...
python tts.py
if errorlevel 1 (
    echo tts.py 执行失败，程序退出
    pause
    exit /b 1
)
echo 运行 source.py...
python source.py
if errorlevel 1 (
    echo tts.py 执行失败，程序退出
    pause
    exit /b 1
)
echo 运行 creat_videos.py...
python creat_videos.py
if errorlevel 1 (
    echo tts.py 执行失败，程序退出
    pause
    exit /b 1
)

echo 所有脚本执行完成！
pause