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
  set /p INSTALL_PYSERIAL=Install pyserial now? [Y/N]: 
  if /I not "!INSTALL_PYSERIAL!"=="Y" (
    echo OCA needs pyserial to open a serial port.
    pause
    goto :eof
  )

  %PYTHON_CMD% -m pip install pyserial
  if errorlevel 1 (
    echo Automatic pyserial installation failed.
    pause
    goto :eof
  )
)

where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw -3 "%~dp0can_analyzer_gui.py"
  goto :eof
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%~dp0can_analyzer_gui.py"
  goto :eof
)

%PYTHON_CMD% "%~dp0can_analyzer_gui.py"
if errorlevel 1 pause
