# ============================================================
# MODEL LOADER
# ============================================================
#
# Loads the fast.ai tomato classifier.
#
# In production (Render), the .pkl file isn't committed to
# the repo — it's downloaded from Hugging Face on first start.
# In local dev, if the file is already present, no download
# happens.
#
# Set MODEL_URL in .env or Render env vars to override the
# default. If empty, the download is skipped.
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


def _download_model(url: str, dest: Path) -> None:
    """
    Stream-download the model file to `dest`.
    Handles the ~103 MB file without loading it all in memory.
    """

    print(f"Model not found at {dest}. Downloading from {url}...")

    tmp = dest.with_suffix(dest.suffix + ".part")

    with httpx.stream(
        "GET",
        url,
        follow_redirects=True,
        timeout=httpx.Timeout(300.0, connect=15.0),
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
                    print(f"  {pct:5.1f}%  {downloaded/1e6:.1f} MB")

    tmp.rename(dest)

    print(f"Model downloaded to {dest}")


def _ensure_model() -> None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 0:
        return

    if not MODEL_URL:
        raise RuntimeError(
            f"Model file missing and MODEL_URL is not set."
        )

    _download_model(MODEL_URL, MODEL_PATH)


_ensure_model()
learn = load_learner(MODEL_PATH)


def predict(image_bytes, crop_name="Tomato"):
    """
    Run inference on an image.

    Returns:
        { "disease": str, "confidence": float }
    """

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    prediction, index, probabilities = learn.predict(image)

    return {
        "disease": str(prediction),
        "confidence": float(probabilities[index]),
    }