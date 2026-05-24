import os
import sys


PROJECT_DIR = os.environ.get(
    "PROJECT_DIR",
    "/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject",
)

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app as application  # noqa: E402
