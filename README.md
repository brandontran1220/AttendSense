# AttendSense (Local Edge-Fog Attendance System)

AttendSense is a privacy-first, fully local attendance system:
- `edge` runs on Jetson Nano and performs face detection/recognition.
- `fog` runs on a laptop and manages attendance/session state + dashboard.
- Communication is local Wi-Fi only (`HTTP POST /event` with JSON).
- No cloud services are used.
- Raw video frames/images are never persisted to disk.

## Architecture

- Edge device:
  - Captures live video using OpenCV.
  - Detects faces and generates embeddings using `face_recognition`.
  - Compares embeddings against locally stored enrolled embeddings.
  - Creates attendance events with:
    - `person_id`
    - `timestamp` (ISO-8601)
    - `confidence` (0.0 to 1.0)
    - `camera_id`
  - Applies per-person edge rate limiting (`30s` default).
  - Sends events to fog `/event`.
  - If network fails, queues events in memory and retries every `10s`.

- Fog device:
  - Flask server with `POST /event`.
  - Validates incoming JSON payloads.
  - Applies deduplication (`person_id -> last_event_time`, 30s default).
  - Persists valid events in SQLite.
  - Maintains class session state and attendance status.
  - Serves password-protected dashboard at `GET /`.

## Project Structure

```text
AttendSense/
  edge/
    config/config.json
    camera_handler.py
    config.py
    demo_mode.py
    enrollment.py
    event_sender.py
    main.py
    rate_limiter.py
    recognition.py
    data/
  fog/
    app.py
    config.py
    db.py
    init_db.py
    policy.py
    session_manager.py
    data/students.json
    templates/
      login.html
      dashboard.html
    static/style.css
  dependencies/
    wheelhouse/
    download_deps.ps1
    download_deps.sh
    README.md
  requirements.txt
```

## Prerequisites

- Python 3.10+ on both devices.
- Jetson Nano camera configured and accessible from OpenCV.
- Both devices connected to the same local Wi-Fi network.
- Fog laptop reachable from Jetson via local IP (example `192.168.1.10`).

## 1) Install Python Dependencies

### Option A: Online install

From project root on each device:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Platform note:
- On Windows (typical fog laptop setup), `requirements.txt` skips `face_recognition` and `dlib`.
- On Linux/Jetson (edge setup), `requirements.txt` includes `face_recognition` and `dlib`.
- If you intentionally build edge on Windows, install Visual Studio C++ Build Tools + CMake first.

Temporary Windows edge smoke test (optional):
- Use this only to validate flow before moving edge to Jetson Nano.
- Install fog-safe requirements first, then add a prebuilt `dlib` wheel package:

```powershell
py -3.10 -m venv .venv-edge-win
.venv-edge-win\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install dlib-bin==19.24.6
python -m pip install face_recognition==1.3.0 --no-deps
python -m pip install face-recognition-models==0.3.0 Pillow
```

Then from `edge/`:

```powershell
python main.py demo
```

If `pip` warns that `face-recognition` requires `dlib`, that warning is expected in this temporary workaround.

### Option B: Prepare offline dependency bundle

From project root:

Windows:

```powershell
./dependencies/download_deps.ps1
```

Linux/macOS:

```bash
bash ./dependencies/download_deps.sh
```

This downloads packages into `dependencies/wheelhouse/`.

Offline install:

```bash
python -m pip install --no-index --find-links dependencies/wheelhouse -r requirements.txt
```

## 2) Configure Fog and Edge

### Fog student roster

Edit:
- `fog/data/students.json`

Example:

```json
[
  { "person_id": "student_001", "name": "Alice" },
  { "person_id": "student_002", "name": "Bob" }
]
```

### Edge runtime config

Edit:
- `edge/config/config.json`

Set these values for your network/environment:
- `fog_host` (laptop IP on local Wi-Fi)
- `fog_port`
- `camera_id`
- `confidence_threshold`
- `rate_limit_seconds`
- `retry_interval_seconds`

## 3) Initialize and Run Fog Manager (Laptop)

From `fog/`:

```bash
python init_db.py
python app.py
```

Server starts at:
- `http://0.0.0.0:5000`

Dashboard login credentials (hardcoded):
- username: `admin`
- password: `attendsense123`

## 4) Enroll Faces on Edge Device (Jetson Nano)

From `edge/`:

```bash
python main.py enroll --person-id [studentid] --samples 8
python main.py enroll --person-id [studentid] --samples 8
```

Notes:
- Enrollment stores embeddings only (`edge/data/known_faces.pkl`).
- No raw frames/images are saved.
- Press `q` to stop enrollment early.

## 5) Run Edge in Live Mode

From `edge/`:

```bash
python main.py run
```

Optional headless mode:

```bash
python main.py run --no-preview
```

## 6) Run Edge in Demo Mode (No Camera Needed)

From `edge/`:

```bash
python main.py demo
```

Demo mode emits fake events every 15 seconds (configurable).

## 7) Event API Contract

Endpoint:
- `POST /event`

JSON payload:

```json
{
  "person_id": "student_001",
  "timestamp": "2026-03-01T22:30:00+00:00",
  "confidence": 0.87,
  "camera_id": "jetson_nano_cam_1"
}
```

## 8) Test with curl

### Send valid event

```bash
curl -X POST http://127.0.0.1:5000/event \
  -H "Content-Type: application/json" \
  -d '{
    "person_id":"student_001",
    "timestamp":"2026-03-01T22:30:00+00:00",
    "confidence":0.91,
    "camera_id":"jetson_nano_cam_1"
  }'
```

### Send invalid payload (should return 400)

```bash
curl -X POST http://127.0.0.1:5000/event \
  -H "Content-Type: application/json" \
  -d '{"person_id":"", "timestamp":"bad", "confidence":"x", "camera_id":""}'
```

## 9) SQLite Schema

AttendSense creates and uses these tables:

- `sessions(id, class_name, start_time, end_time)`
- `attendance_events(id, person_id, timestamp, confidence, camera_id)`
- `attendance_status(id, session_id, person_id, present)`

Behavior:
- A student is marked present when at least one valid event is received during an active session.
- Dashboard shows:
  - current session name
  - all students
  - Present/Absent status
  - total present count
  - last detection timestamp per student
- Past session history is available at `GET /sessions` to review ended sessions.
- Dashboard auto-refreshes every 5 seconds with lightweight JavaScript.

## Privacy and Local-Only Guarantees

- Face embeddings are stored locally on edge in `pickle` format.
- Attendance events are stored locally in fog SQLite.
- No cloud endpoints, cloud SDKs, or external data storage are used.
- Raw video frames/images are processed in memory only.
