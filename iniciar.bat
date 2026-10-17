@echo off
rem Doble clic para abrir la aplicacion. Ver scripts\iniciar.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar.ps1" %*
