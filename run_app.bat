@echo off
chcp 65001
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=utf-8
python -m streamlit run app.py
pause