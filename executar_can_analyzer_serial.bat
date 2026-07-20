@echo off
setlocal EnableDelayedExpansion

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
  goto :run
)

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=python"
  goto :run
)

echo Python was not found.
echo Install Python 3 and enable "Add python.exe to PATH" during installation.
pause
goto :eof

:run
%PYTHON_CMD% -c "import serial" >nul 2>nul
if errorlevel 1 (
  echo pyserial was not found in the selected Python installation.
  echo.
  echo Installation command:
  echo %PYTHON_CMD% -m pip install pyserial
  echo.
  set /p INSTALL_PYSERIAL=Install pyserial now? [Y/N]: 
  if /I not "!INSTALL_PYSERIAL!"=="Y" (
    echo.
    echo OCA needs pyserial to open a serial port.
    echo Install it manually with: %PYTHON_CMD% -m pip install pyserial
    pause
    goto :eof
  )

  %PYTHON_CMD% -m pip install pyserial
  if errorlevel 1 (
    echo.
    echo Automatic pyserial installation failed.
    echo Open Command Prompt and run:
    echo %PYTHON_CMD% -m pip install pyserial
    pause
    goto :eof
  )
)

if not "%~1"=="" (
  %PYTHON_CMD% "%~dp0can_analyzer_serial.py" %*
  if errorlevel 1 pause
  goto :eof
)

%PYTHON_CMD% "%~dp0can_analyzer_serial.py" --list
echo.
set /p COM_PORT=Enter the Open CAN Analyzer serial port (example COM7): 
if "%COM_PORT%"=="" (
  echo No serial port was provided.
  pause
  goto :eof
)

%PYTHON_CMD% "%~dp0can_analyzer_serial.py" --port %COM_PORT%
pause
