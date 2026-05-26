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

- Save workout sessions and meals by date
- Add multi-set workouts with kg/lb input, equipment, location, rest timer, RPE, and memo
- Track PRs, body-part balance, yearly/monthly/weekly summaries, and exercise trends
- Manage workout locations and location-specific equipment history
- Use settings password lock for personal write access while visitors stay read-only
- Export/restore data with automatic safety backups
- SQLite database stored in `instance/workout.db`
- PWA manifest and service worker for app-like mobile use

## Deploy to PythonAnywhere

See [DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md).
