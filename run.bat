@echo off
echo ��ʼ���нű�...

REM �������⻷��
echo �������⻷��...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo ����: δ�ҵ����⻷������������ setup.bat
    pause
    exit /b 1
)

echo ���� get_datasets.py...
python get_datasets.py
if errorlevel 1 (
    echo get_datasets.py ִ��ʧ�ܣ������˳�
    pause
    exit /b 1
)

echo ���� get_tags.py...
python get_tags.py
if errorlevel 1 (
    echo get_tags.py ִ��ʧ�ܣ������˳�
    pause
    exit /b 1
)

echo ���� llm.py...
python llm.py
if errorlevel 1 (
    echo llm.py ִ��ʧ�ܣ������˳�
    pause
    exit /b 1
)

echo ���� tts.py...
python tts.py
if errorlevel 1 (
    echo tts.py ִ��ʧ�ܣ������˳�
    pause
    exit /b 1
)
echo ���� source.py...
python source.py
if errorlevel 1 (
    echo tts.py ִ��ʧ�ܣ������˳�
    pause
    exit /b 1
)
echo ���� creat_videos.py...
python creat_videos.py
if errorlevel 1 (
    echo tts.py ִ��ʧ�ܣ������˳�
    pause
    exit /b 1
)

echo ���нű�ִ����ɣ�
pause