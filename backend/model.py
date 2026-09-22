# ============================================================
# MODEL LOADER
# ============================================================
#
# Loads the fast.ai tomato classifier.
#
# Design notes:
#   - The model file is NOT committed to the repo (it's 103 MB).
#   - On deployment, it's downloaded from Hugging Face on first
#     prediction request, not at import time.
#   - Lazy-loading matters for Render: if we load at import time,
#     uvicorn doesn't bind to its port until the model is ready.
#     Render's port scanner times out after ~90 seconds and kills
#     the deploy. Loading lazily lets uvicorn bind in ~5 seconds.
#   - Locally, if the .pkl is already next to this file, no
#     download happens.
# ============================================================

import os
from pathlib import Path

import httpx
from fastai.learner import load_learner
from PIL import Image
import io


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "tomato_disease_model.pkl"

DEFAULT_MODEL_URL = (
    "https://huggingface.co/WICKED0/pandora-crop-classifier/"
    "resolve/main/tomato_disease_model.pkl"
)

MODEL_URL = os.getenv("MODEL_URL", DEFAULT_MODEL_URL)


# ============================================================
# DOWNLOAD
# ============================================================

def _download_model(url: str, dest: Path) -> None:
    """
    Stream-download the model file to `dest`.
    Handles the ~103 MB file without loading it all in memory.
    """

    print(f"[model] Not found at {dest}. Downloading from {url}...")

    tmp = dest.with_suffix(dest.suffix + ".part")

    with httpx.stream(
        "GET",
        url,
        follow_redirects=True,
        timeout=httpx.Timeout(600.0, connect=30.0),
    ) as response:

        response.raise_for_status()

        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        with open(tmp, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)

                if total:
                    pct = (downloaded / total) * 100
                    # Print less often to keep logs clean
                    if downloaded % (10 * 1024 * 1024) < (1024 * 1024):
                        print(f"[model]   {pct:5.1f}%  {downloaded/1e6:.1f} MB")

    tmp.rename(dest)
    print(f"[model] Downloaded to {dest} ({downloaded/1e6:.1f} MB)")


def _ensure_model() -> None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 0:
        print(f"[model] Found existing model at {MODEL_PATH}")
        return

    if not MODEL_URL:
        raise RuntimeError("Model file missing and MODEL_URL is not set.")

    _download_model(MODEL_URL, MODEL_PATH)


# ============================================================
# LAZY LEARNER
# ============================================================

_learn = None


def _get_learn():
    """
    Lazy-load the model on first prediction.

    This lets FastAPI/uvicorn bind to its port immediately so
    platforms like Render see the service as up before the model
    download + load completes.
    """
    global _learn
    if _learn is None:
        _ensure_model()
        print("[model] Loading learner...")
        _learn = load_learner(MODEL_PATH)
        print("[model] Learner ready.")
    return _learn


# ============================================================
# PUBLIC
# ============================================================

def predict(image_bytes, crop_name="Tomato"):
    """
    Run inference on an image.

    Returns:
        { "disease": str, "confidence": float }
    """

    learn = _get_learn()

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    prediction, index, probabilities = learn.predict(image)

    return {
        "disease": str(prediction),
        "confidence": float(probabilities[index]),
    }