import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MIPROXIMOCARRO_TRM_OFFLINE", "1")
os.environ.setdefault("MIPROXIMOCARRO_RATE_LIMIT", "10000/minute")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from backend.app.main import app
    return TestClient(app)
