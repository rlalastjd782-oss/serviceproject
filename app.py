from __future__ import annotations

import sys
from importlib import import_module

app_module = import_module("health_tracker.app")

if __name__ == "__main__":
    app_module.main()
else:
    sys.modules[__name__] = app_module
