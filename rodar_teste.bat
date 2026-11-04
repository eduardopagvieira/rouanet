@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set CONDA=%USERPROFILE%\miniconda3
set PY=%CONDA%\python.exe
if not exist "%PY%" set PY=python
rem Sem estas pastas no PATH o Python do miniconda nao acha as DLLs do SSL e o pip falha
set PATH=%CONDA%;%CONDA%\Library\mingw-w64\bin;%CONDA%\Library\usr\bin;%CONDA%\Library\bin;%CONDA%\Scripts;%PATH%
echo Rodando teste da coleta. A janela fecha sozinha ao terminar.
(
  echo === Python ===
  "%PY%" --version
  echo === Instalando dependencias ===
  "%PY%" -m pip install --quiet requests pandas
  echo === Teste da coleta ===
  "%PY%" coletar_salic.py --teste
  echo === Fim ===
) > log_teste.txt 2>&1
echo Pronto. Resultado salvo em log_teste.txt
timeout /t 5 > nul
