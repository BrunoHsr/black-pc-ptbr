@echo off
rem Aplica a traducao PT-BR do BLACK. Uso: aplicar.bat [pasta do BLACK]   |   aplicar.bat --restaurar [pasta]
chcp 65001 >nul
python "%~dp0patch\aplicar.py" %*
echo.
pause
