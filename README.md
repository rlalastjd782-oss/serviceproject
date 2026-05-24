# serviceproject

Mobile-first workout tracker built as a Flask + SQLite PWA.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` on this computer.

To use it from a phone on the same Wi-Fi, run:

```powershell
python app.py --host 0.0.0.0
```

Then open `http://YOUR_PC_IP:5000` from the phone browser and add it to the home screen.

## Features

- Save workout sessions by date
- Add exercise sets with weight, reps, and memo
- View recent workout history
- SQLite database stored in `instance/workout.db`
- PWA manifest and service worker for app-like mobile use

## Deploy to PythonAnywhere

See [DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md).
