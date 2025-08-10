"""Basic smoke tests for the FastAPI backend.

These tests exercise a minimal slice of functionality across the data
science, MMM and creative endpoints. They use the FastAPI TestClient
against the app defined in ``main.py``. Running these tests ensures
that the primary routes respond without raising errors and that
side‑effects like file writes occur in isolated temporary directories.
"""

import base64
import io
import json
import os
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
import pytest

# Import the FastAPI app.  This import triggers environment variable
# resolution; ensure DATA_DIR and IMAGE_LIBRARY_DIR are set prior to
# importing so that the app mounts static directories correctly.


@pytest.fixture
def temp_dirs(tmp_path, monkeypatch):
    """Set up temporary directories for data and image library.

    Uses monkeypatch to override environment variables so that the app
    writes to a sandboxed location during tests.
    """
    data_dir = tmp_path / "data"
    image_dir = tmp_path / "image_library"
    data_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("IMAGE_LIBRARY_DIR", str(image_dir))
    # Provide dummy values for Redis to avoid connection attempts
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    # Ensure no Vertex calls are made
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "")
    return data_dir, image_dir


@pytest.fixture
def client(temp_dirs):
    """Initialise the TestClient with patched environment variables.

    Because the backend code lives in a directory with a hyphen in its
    name (``agent-python-backend``), it is not importable as a normal
    Python package.  We append that directory to ``sys.path`` to allow
    importing ``main`` dynamically for the tests.
    """
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parents[2] / "agent-python-backend"
    sys.path.insert(0, str(backend_dir))
    from main import app  # type: ignore
    return TestClient(app)


def test_preview_endpoint(client, temp_dirs):
    data_dir, _ = temp_dirs
    # Create a tiny CSV file
    df = pd.DataFrame({"sales": [10, 20, 30], "tv_spend": [1, 2, 3]})
    dataset_path = data_dir / "tiny_dataset.csv"
    df.to_csv(dataset_path, index=False)
    # Request preview
    resp = client.get(f"/preview/{dataset_path.name}")
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["columns"] == ["sales", "tv_spend"]
    assert len(preview["data"]) > 0


def test_analyze_bayesian(client, temp_dirs):
    data_dir, _ = temp_dirs
    # Create a small but valid MMM dataset
    df = pd.DataFrame({
        "sales": [100, 120, 130, 150],
        "tv_spend": [10, 15, 20, 25],
        "radio_spend": [5, 7, 6, 9],
    })
    file_path = data_dir / "mmm_small.csv"
    df.to_csv(file_path, index=False)
    form_data = {
        "dataset_filename": file_path.name,
        "prompt": "Evaluate channel ROI.",
        "model_type": "bayesian",
        "revenue_target": "0",
    }
    resp = client.post("/analyze", data=form_data)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    # Expect keys for model_id, plots and summary
    assert "model_id" in result
    assert "plots" in result and isinstance(result["plots"], dict)
    assert "summary" in result
    # Ensure that at least one plot file exists on disk
    model_dir = Path(data_dir) / "models" / result["model_id"]
    assert model_dir.exists() and any(model_dir.glob("*.png"))


def test_library_save_and_list(client, temp_dirs):
    _, image_dir = temp_dirs
    # Create a simple black square JPEG in memory
    from PIL import Image  # type: ignore
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    data_url = f"data:image/jpeg;base64,{b64}"
    # Save the image via API
    resp = client.post("/library/images/save", data={"data_url": data_url})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "orig" in payload and payload["orig"].startswith("/image_library/orig/")
    # List assets
    resp2 = client.get("/library/assets")
    assert resp2.status_code == 200, resp2.text
    assets = resp2.json().get("assets", [])
    assert len(assets) >= 1
    # Check that the saved asset appears in the list
    saved_id = Path(payload["orig"]).stem
    assert any(a["id"] == saved_id for a in assets)