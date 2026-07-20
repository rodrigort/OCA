# Building OCA

## Common preparation

Use a clean Python 3.9+ virtual environment on the target operating system:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python tools/validate_project.py
python -m unittest discover -s tests -v
python tools/build_package.py
```

PyInstaller produces `dist/OpenCANAnalyzer`. Builds are platform-specific; build Windows on
Windows, Linux on Linux and macOS on macOS. The package includes profiles, translations,
public examples and `cantools` support.

## Windows

Install Python with Tcl/Tk, then run `powershell -ExecutionPolicy Bypass -File tools/build_windows.ps1`.
Test serial discovery and DBC loading on a clean Windows account. Code signing is not included.

## Linux

Install the distribution's Python, Tk and virtual-environment packages (often `python3-tk`
and `python3-venv`), then run `./tools/build_desktop.sh`. Serial access may require membership
in a group such as `dialout`; do not recommend running the application as root.

## macOS

Use a Python distribution with Tk support and run `./tools/build_desktop.sh`. Test on each
supported CPU architecture. Signing, hardened runtime and notarization require an Apple
Developer identity and are intentionally outside the default script.

## Portable configuration

Create an empty `.portable` file beside the executable or set `OCA_PORTABLE=1`. Ensure that
location is writable. Without portable mode, OCA follows the platform user-configuration
directory. Never distribute a real `config.json`, capture or private DBC with a release.
