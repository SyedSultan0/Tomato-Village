from fastai.learner import load_learner
from PIL import Image
import io

learn = load_learner("tomato_disease_model.pkl")


def predict(image_bytes):

    # Convert uploaded bytes into a PIL image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Let FastAI handle the preprocessing
    prediction, index, probabilities = learn.predict(image)

    return {
        "disease": str(prediction),
        "confidence": float(probabilities[index])
    }