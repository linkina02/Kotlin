@echo off

set RUNTIME_MSIL=%~dp0runtime-net\runtime.msil

set PYTHON="C:\Users\Julia\AppData\Local\Programs\Python\Python310\python.exe"

if exist "%~dp0.\bin\_props.bat" call "%~dp0.\bin\_props.bat"
if exist "%~dp0.\_props.bat" call "%~dp0.\_props.bat"


if "%~1"=="" (
  (
    echo Usage:
    echo   %~nx0 src
  ) 1>&2
  exit 1
)
if not exist "%~1" (
  (
    echo File "%~1" not exists
  ) 1>&2
  exit 2
)


@REM del /f /q "%~dpn1.exe" "%~dpn1.msil"
@REM echo before
PYTHON "%~dp0\main.py" —msil-only "%~dpnx1" >"%~dpn1.msil"
@REM echo "%~dpnx1" dpnx1
@REM echo "%~dpn1.msil" for msil
@REM echo after
set STATUS=%ERRORLEVEL%
if not "%STATUS%"=="0" (
@REM echo "%STATUS%"
@REM echo error
  del /f /q "%~dpn1.msil"
  exit %STATUS%
)

"%~dp0.\bin\ilasm" /out:"%~dpn1.exe" "%~dpn1.msil" "%RUNTIME_MSIL%"
:: del /f /q "%~dpn1.msil"
