@echo off
rem Dispatch Engine for Windows: run.cmd [start^|check^|stop^|logs] [--db]
rem Works from PowerShell, cmd, or by double-clicking. Needs only Docker Desktop.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run.ps1" %*
exit /b %ERRORLEVEL%
