# Dependency Bundle

This folder is for downloading offline-installable Python packages.

## Quick use

From the project root:

```powershell
./dependencies/download_deps.ps1 -Python .venv\Scripts\python.exe
```

or on Linux/macOS:

```bash
bash ./dependencies/download_deps.sh
```

Packages will be saved to `dependencies/wheelhouse/`.

## Offline install

On the target device:

```bash
python -m pip install --no-index --find-links dependencies/wheelhouse -r requirements.txt
```

## Notes

- Download wheels using the same Python version as the target runtime (for example, Python 3.10 wheels for a 3.10 target).
- On Windows, `requirements.txt` skips edge-only `face_recognition`/`dlib`; those install on Linux/Jetson edge devices.
- `face_recognition` depends on `dlib`; Jetson Nano may require a source build for some versions.
- If a wheel is unavailable for your platform, download source packages (`.tar.gz`) and build locally.
