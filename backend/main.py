
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from pydantic import BaseModel

from sqlalchemy.orm import Session

from datetime import date, datetime

from pathlib import Path

import uuid


from model import predict
from weather import get_weather
from risk_engine import calculate_risk

from database import (
    SessionLocal,
    Farmer,
    Farm,
    Crop,
    CropSeason,
    HealthReport,
    Image,
    AIPrediction,
    WeatherRecord,
    RiskAssessment
)


app = FastAPI(
    title="Tomato Disease Detection API",
    description="AI-powered crop disease detection and health monitoring system",
    version="1.0.0"
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# RESPONSE MODELS
# ============================================================

class PredictionResponse(BaseModel):
    disease: str
    confidence: float
    crop: str
    model: str


class FarmerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    preferred_language: str = "English"


class FarmCreate(BaseModel):
    farmer_id: int
    farm_name: str
    latitude: float
    longitude: float
    district: str
    state: str


class CropCreate(BaseModel):
    name: str
    scientific_name: str | None = None
    category: str | None = None
    description: str | None = None


class CropSeasonCreate(BaseModel):
    farm_id: int
    crop_id: int
    variety: str | None = None
    planting_date: date | None = None
    expected_harvest_date: date | None = None


# ============================================================
# BASIC ROUTES
# ============================================================

@app.get("/")
def root():

    return {
        "message": "Tomato-Village API is running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }


# ============================================================
# MODEL PREDICTION
# ============================================================

@app.post("/predict", response_model=PredictionResponse)
async def predict_disease(
    file: UploadFile = File(...)
):

    if not file.content_type:

        raise HTTPException(
            status_code=400,
            detail="File type could not be determined."
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp"
    }

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG and WEBP images are allowed."
        )

    image_bytes = await file.read()

    if not image_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty."
        )

    try:

        result = predict(image_bytes)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

    return {
        "disease": result["disease"],
        "confidence": result["confidence"],
        "crop": "Tomato",
        "model": "tomato-disease-v1"
    }


# ============================================================
# FARMER
# ============================================================

@app.post("/farmers")
def create_farmer(
    farmer: FarmerCreate,
    db: Session = Depends(get_db)
):

    existing_farmer = (
        db.query(Farmer)
        .filter(Farmer.phone == farmer.phone)
        .first()
    )

    if existing_farmer:

        raise HTTPException(
            status_code=400,
            detail="A farmer with this phone number already exists."
        )

    new_farmer = Farmer(
        name=farmer.name,
        phone=farmer.phone,
        email=farmer.email,
        preferred_language=farmer.preferred_language
    )

    db.add(new_farmer)
    db.commit()
    db.refresh(new_farmer)

    return {
        "message": "Farmer created successfully",
        "farmer_id": new_farmer.id,
        "name": new_farmer.name,
        "phone": new_farmer.phone,
        "preferred_language": new_farmer.preferred_language
    }


# ============================================================
# FARM
# ============================================================

@app.post("/farms")
def create_farm(
    farm: FarmCreate,
    db: Session = Depends(get_db)
):

    farmer = (
        db.query(Farmer)
        .filter(Farmer.id == farm.farmer_id)
        .first()
    )

    if not farmer:

        raise HTTPException(
            status_code=404,
            detail="Farmer not found."
        )

    new_farm = Farm(
        farmer_id=farm.farmer_id,
        farm_name=farm.farm_name,
        latitude=farm.latitude,
        longitude=farm.longitude,
        district=farm.district,
        state=farm.state
    )

    db.add(new_farm)
    db.commit()
    db.refresh(new_farm)

    return {
        "message": "Farm created successfully",
        "farm_id": new_farm.id,
        "farmer_id": new_farm.farmer_id,
        "farm_name": new_farm.farm_name,
        "location": {
            "latitude": new_farm.latitude,
            "longitude": new_farm.longitude
        },
        "district": new_farm.district,
        "state": new_farm.state
    }


# ============================================================
# CROP
# ============================================================

@app.post("/crops")
def create_crop(
    crop: CropCreate,
    db: Session = Depends(get_db)
):

    existing_crop = (
        db.query(Crop)
        .filter(Crop.name == crop.name)
        .first()
    )

    if existing_crop:

        raise HTTPException(
            status_code=400,
            detail="This crop already exists."
        )

    new_crop = Crop(
        name=crop.name,
        scientific_name=crop.scientific_name,
        category=crop.category,
        description=crop.description
    )

    db.add(new_crop)
    db.commit()
    db.refresh(new_crop)

    return {
        "message": "Crop created successfully",
        "crop_id": new_crop.id,
        "name": new_crop.name
    }


# ============================================================
# CROP SEASON
# ============================================================

@app.post("/crop-seasons")
def create_crop_season(
    crop_season: CropSeasonCreate,
    db: Session = Depends(get_db)
):

    farm = (
        db.query(Farm)
        .filter(Farm.id == crop_season.farm_id)
        .first()
    )

    if not farm:

        raise HTTPException(
            status_code=404,
            detail="Farm not found."
        )

    crop = (
        db.query(Crop)
        .filter(Crop.id == crop_season.crop_id)
        .first()
    )

    if not crop:

        raise HTTPException(
            status_code=404,
            detail="Crop not found."
        )

    new_season = CropSeason(
        farm_id=crop_season.farm_id,
        crop_id=crop_season.crop_id,
        variety=crop_season.variety,
        planting_date=crop_season.planting_date,
        expected_harvest_date=crop_season.expected_harvest_date,
        status="ACTIVE"
    )

    db.add(new_season)
    db.commit()
    db.refresh(new_season)

    return {
        "message": "Crop season created successfully",
        "crop_season_id": new_season.id,
        "farm_id": new_season.farm_id,
        "crop_id": new_season.crop_id,
        "variety": new_season.variety,
        "status": new_season.status
    }


# ============================================================
# WEATHER HELPERS
# ============================================================

def get_weather_condition(weather_code):

    weather_codes = {
        0: "Clear sky",

        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",

        45: "Fog",
        48: "Depositing rime fog",

        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",

        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",

        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",

        66: "Light freezing rain",
        67: "Heavy freezing rain",

        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",

        77: "Snow grains",

        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",

        85: "Slight snow showers",
        86: "Heavy snow showers",

        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    return weather_codes.get(
        weather_code,
        f"Weather code {weather_code}"
    )


def get_next_hour_rain_probability(weather_data):

    hourly = weather_data.get("hourly", {})

    probabilities = hourly.get(
        "precipitation_probability",
        []
    )

    if probabilities:

        try:
            return float(probabilities[0])

        except (ValueError, TypeError):
            return None

    return None


# ============================================================
# HEALTH REPORT
# ============================================================

@app.post("/health-reports")
async def create_health_report(
    farm_id: int,
    crop_season_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Validate image
    # --------------------------------------------------------

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp"
    }

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG and WEBP images are allowed."
        )

    image_bytes = await file.read()

    if not image_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty."
        )

    # --------------------------------------------------------
    # Validate farm
    # --------------------------------------------------------

    farm = (
        db.query(Farm)
        .filter(Farm.id == farm_id)
        .first()
    )

    if not farm:

        raise HTTPException(
            status_code=404,
            detail="Farm not found."
        )

    # --------------------------------------------------------
    # Validate crop season
    # --------------------------------------------------------

    crop_season = (
        db.query(CropSeason)
        .filter(CropSeason.id == crop_season_id)
        .first()
    )

    if not crop_season:

        raise HTTPException(
            status_code=404,
            detail="Crop season not found."
        )

    # --------------------------------------------------------
    # Make sure crop season belongs to selected farm
    # --------------------------------------------------------

    if crop_season.farm_id != farm_id:

        raise HTTPException(
            status_code=400,
            detail="Crop season does not belong to this farm."
        )

    # --------------------------------------------------------
    # AI prediction
    # --------------------------------------------------------

    try:

        prediction = predict(image_bytes)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

    # --------------------------------------------------------
    # Create health report
    # --------------------------------------------------------

    health_report = HealthReport(
        farm_id=farm_id,
        crop_season_id=crop_season_id,
        latitude=farm.latitude,
        longitude=farm.longitude,
        source="FARMER",
        status="COMPLETED"
    )

    db.add(health_report)
    db.flush()

    # --------------------------------------------------------
    # Save image
    # --------------------------------------------------------

    file_extension = Path(file.filename).suffix.lower()

    unique_filename = (
        f"{uuid.uuid4().hex}{file_extension}"
    )

    file_path = UPLOAD_DIR / unique_filename

    with open(file_path, "wb") as buffer:

        buffer.write(image_bytes)

    image_record = Image(
        health_report_id=health_report.id,
        file_name=file.filename,
        file_size=len(image_bytes),
        mime_type=file.content_type,
        storage_path=str(file_path)
    )

    db.add(image_record)

    # --------------------------------------------------------
    # Save AI prediction
    # --------------------------------------------------------

    prediction_record = AIPrediction(
        health_report_id=health_report.id,
        model_name="tomato-disease-v1",
        model_version="1.0",
        prediction_type="CLASSIFICATION",
        predicted_class=prediction["disease"],
        confidence=prediction["confidence"],
        prediction_data=prediction
    )

    db.add(prediction_record)

    # --------------------------------------------------------
    # Fetch weather automatically
    # --------------------------------------------------------

    weather_saved = False
    weather_error = None
    weather_record = None

    risk_record = None
    risk_error = None

    try:

        weather_data = await get_weather(
            farm.latitude,
            farm.longitude
        )

        current_weather = weather_data.get(
            "current",
            {}
        )

        weather_code = current_weather.get(
            "weather_code"
        )

        observed_at = None

        weather_time = current_weather.get(
            "time"
        )

        if weather_time:

            try:

                observed_at = datetime.fromisoformat(
                    weather_time
                )

            except ValueError:

                observed_at = datetime.utcnow()

        weather_record = WeatherRecord(
            health_report_id=health_report.id,

            latitude=farm.latitude,
            longitude=farm.longitude,

            temperature=current_weather.get(
                "temperature_2m"
            ),

            humidity=current_weather.get(
                "relative_humidity_2m"
            ),

            rainfall=current_weather.get(
                "precipitation"
            ),

            rain_probability=get_next_hour_rain_probability(
                weather_data
            ),

            wind_speed=current_weather.get(
                "wind_speed_10m"
            ),

            weather_condition=get_weather_condition(
                weather_code
            ),

            raw_data=weather_data,

            observed_at=observed_at,

            provider="OPEN_METEO"
        )

        db.add(weather_record)

        weather_saved = True

        # ----------------------------------------------------
        # Calculate environmental risk
        # ----------------------------------------------------

        try:

            risk_result = calculate_risk(
                disease=prediction["disease"],
                confidence=prediction["confidence"],
                weather_data=weather_data
            )

            risk_record = RiskAssessment(
                health_report_id=health_report.id,
                risk_score=risk_result["risk_score"],
                risk_level=risk_result["risk_level"],
                calculation_method=risk_result["engine_version"],
                factors=risk_result["factors"]
            )

            db.add(risk_record)

        except Exception as e:

            risk_error = str(e)

            print(
                "Risk calculation failed:",
                risk_error
            )

    except Exception as e:

        weather_error = str(e)

        print(
            "Weather retrieval failed:",
            weather_error
        )

    # --------------------------------------------------------
    # Commit everything
    # --------------------------------------------------------

    try:

        db.commit()

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database operation failed: {str(e)}"
        )

    # --------------------------------------------------------
    # Refresh saved records
    # --------------------------------------------------------

    db.refresh(health_report)
    db.refresh(image_record)
    db.refresh(prediction_record)

    if weather_record:

        db.refresh(weather_record)

    if risk_record:

        db.refresh(risk_record)

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    response = {

        "message": "Health report created successfully",

        "health_report": {
            "id": health_report.id,
            "farm_id": health_report.farm_id,
            "crop_season_id": health_report.crop_season_id,
            "latitude": health_report.latitude,
            "longitude": health_report.longitude,
            "source": health_report.source,
            "status": health_report.status,
            "reported_at": health_report.reported_at
        },

        "image": {
            "id": image_record.id,
            "file_name": image_record.file_name,
            "file_size": image_record.file_size,
            "mime_type": image_record.mime_type,
            "storage_path": image_record.storage_path
        },

        "prediction": {
            "disease": prediction_record.predicted_class,
            "confidence": prediction_record.confidence,
            "model": prediction_record.model_name,
            "model_version": prediction_record.model_version
        },

        "weather": {
            "saved": weather_saved
        },

        "risk": {
            "calculated": risk_record is not None
        }
    }

    # --------------------------------------------------------
    # Weather response
    # --------------------------------------------------------

    if weather_record:

        response["weather"].update({

            "id": weather_record.id,

            "temperature": weather_record.temperature,

            "humidity": weather_record.humidity,

            "rainfall": weather_record.rainfall,

            "rain_probability": weather_record.rain_probability,

            "wind_speed": weather_record.wind_speed,

            "condition": weather_record.weather_condition,

            "provider": weather_record.provider
        })

    else:

        response["weather"]["error"] = weather_error

    # --------------------------------------------------------
    # Risk response
    # --------------------------------------------------------

    if risk_record:

        response["risk"].update({

            "id": risk_record.id,

            "score": risk_record.risk_score,

            "level": risk_record.risk_level,

            "calculation_method": risk_record.calculation_method,

            "factors": risk_record.factors
        })

    else:

        response["risk"]["error"] = risk_error

    return response
