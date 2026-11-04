@echo off
cd /d "%~dp0.."
python -m ai_event_editor.service --configure-plugin
pause
