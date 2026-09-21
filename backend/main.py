from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy import desc

from datetime import date, datetime

from pathlib import Path

import uuid


from model import predict
from weather import get_weather
from risk_engine import calculate_risk
from advisory_engine import generate_advisory
from monitoring_engine import compare_reports
from escalation_engine import decide_escalation
from knowledge_retrieval import retrieve_evidence
from explanation_engine import generate_explanation
from expert_validation import (
    validate_submission,
    serialize_validation,
)
from expert_queue import build_review_queue
from hotspots import find_hotspots
from report_snapshots import (
    _build_report_snapshot,
    _build_escalation,
    _build_evidence_for_report,
    _build_explanation_for_report,
)

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
    RiskAssessment,
    Advisory,
    FollowUp,
    ExpertValidation,
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

def _build_expert_validations_for_report(
    db: Session,
    health_report_id: int,
):
    rows = (
        db.query(ExpertValidation)
        .filter(ExpertValidation.health_report_id == health_report_id)
        .order_by(desc(ExpertValidation.validated_at))
        .all()
    )
    return [serialize_validation(db, row) for row in rows]

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


class FollowUpCreate(BaseModel):
    scheduled_date: date
    farmer_notes: str | None = None

class ExpertValidationCreate(BaseModel):
    expert_id: int
    status: str
    confirmed_condition: str | None = None
    comments: str | None = None

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
def predict_disease(
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

    image_bytes = file.file.read()

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
# MONITORING HELPERS
# ============================================================

# ============================================================
# ESCALATION HELPERS
# ============================================================

def _validate_comparison_linkage(
    db: Session,
    original_report_id: int,
    follow_up_report_id: int
):
    """
    Re-verify at read time that two linked reports belong to the
    same farm and crop season.

    The write path already validates this when a FollowUp row is
    created, so this is defense-in-depth.
    """

    original_report = (
        db.query(HealthReport)
        .filter(HealthReport.id == original_report_id)
        .first()
    )

    follow_up_report = (
        db.query(HealthReport)
        .filter(HealthReport.id == follow_up_report_id)
        .first()
    )

    if not original_report or not follow_up_report:
        raise HTTPException(
            status_code=404,
            detail="One of the linked health reports was not found."
        )

    if original_report.farm_id != follow_up_report.farm_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "The two linked reports belong to different farms. "
                "Comparison is not meaningful."
            )
        )

    if original_report.crop_season_id != follow_up_report.crop_season_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "The two linked reports belong to different crop "
                "seasons. Comparison is not meaningful."
            )
        )
# ============================================================
# EVIDENCE HELPERS
# ============================================================

# ============================================================
# HEALTH REPORT
# ============================================================

@app.post("/health-reports")
def create_health_report(
    farm_id: int,
    crop_season_id: int,
    file: UploadFile = File(...),
    follow_up_id: int | None = None,
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

    image_bytes = file.file.read()

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
    # Validate follow-up linkage if supplied
    # --------------------------------------------------------

    follow_up_record = None

    if follow_up_id is not None:

        follow_up_record = (
            db.query(FollowUp)
            .filter(FollowUp.id == follow_up_id)
            .first()
        )

        if not follow_up_record:

            raise HTTPException(
                status_code=404,
                detail="Follow-up record not found."
            )

        if follow_up_record.status == "COMPLETED":

            raise HTTPException(
                status_code=400,
                detail="This follow-up has already been completed."
            )

        original_report = (
            db.query(HealthReport)
            .filter(
                HealthReport.id ==
                follow_up_record.original_report_id
            )
            .first()
        )

        if not original_report:

            raise HTTPException(
                status_code=400,
                detail="Original health report linked to follow-up was not found."
            )

        if original_report.farm_id != farm_id:

            raise HTTPException(
                status_code=400,
                detail="Follow-up belongs to a different farm."
            )

        if original_report.crop_season_id != crop_season_id:

            raise HTTPException(
                status_code=400,
                detail="Follow-up belongs to a different crop season."
            )

        if follow_up_record.follow_up_report_id is not None:

            raise HTTPException(
                status_code=400,
                detail="This follow-up is already linked to a health report."
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
    # Weather / Risk / Advisory
    # --------------------------------------------------------

    weather_saved = False
    weather_error = None
    weather_record = None

    risk_record = None
    risk_result = None
    risk_error = None

    advisory_record = None
    advisory_result = None
    advisory_error = None

    try:

        weather_data = get_weather(
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

            # ------------------------------------------------
            # Generate deterministic advisory
            # ------------------------------------------------

            try:

                advisory_result = generate_advisory(
                    disease=prediction["disease"],
                    risk_level=risk_result["risk_level"],
                    confidence=prediction["confidence"],
                    weather_snapshot=risk_result.get(
                        "weather_snapshot",
                        {}
                    )
                )

                advisory_record = Advisory(
                    health_report_id=health_report.id,
                    language="English",
                    risk_level=risk_result["risk_level"],
                    advisory_text=advisory_result["summary"],
                    model_name=advisory_result["engine"]["name"],
                    model_version=advisory_result["engine"]["version"],
                    sources=advisory_result["sources"]
                )

                db.add(advisory_record)

            except Exception as e:

                advisory_error = str(e)

                print(
                    "Advisory generation failed:",
                    advisory_error
                )

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
    # Link newly created report to follow-up
    # --------------------------------------------------------

    if follow_up_record:

        follow_up_record.follow_up_report_id = health_report.id
        follow_up_record.completed_at = datetime.utcnow()
        follow_up_record.status = "COMPLETED"

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

    if advisory_record:
        db.refresh(advisory_record)

    if follow_up_record:
        db.refresh(follow_up_record)

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
        },

        "advisory": {
            "generated": advisory_record is not None
        },

        "monitoring": {
            "is_follow_up": follow_up_record is not None,
            "follow_up_id": (
                follow_up_record.id
                if follow_up_record
                else None
            ),
            "original_report_id": (
                follow_up_record.original_report_id
                if follow_up_record
                else None
            )
        }
    }

    # --------------------------------------------------------
    # Escalation decision
    # --------------------------------------------------------

    escalation_comparison = None

    if follow_up_record:

        original_snapshot = _build_report_snapshot(
            db,
            follow_up_record.original_report_id
        )

        current_snapshot = _build_report_snapshot(
            db,
            health_report.id
        )

        if original_snapshot and current_snapshot:

            escalation_comparison = compare_reports(
                original_report=original_snapshot,
                follow_up_report=current_snapshot
            )

    response["escalation"] = _build_escalation(
        db,
        health_report.id,
        comparison=escalation_comparison
    )

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

    # --------------------------------------------------------
    # Advisory response
    # --------------------------------------------------------

    if advisory_record:

        response["advisory"].update({

            "id": advisory_record.id,

            "risk_level": advisory_record.risk_level,

            "summary": advisory_result["summary"],

            "immediate_actions": (
                advisory_result["immediate_actions"]
            ),

            "prevention": (
                advisory_result["prevention"]
            ),

            "monitoring": (
                advisory_result["monitoring"]
            ),

            "expert_referral": (
                advisory_result["expert_referral"]
            ),

            "environmental_modifiers": (
                advisory_result["environmental_modifiers"]
            ),

            "low_confidence_warning": (
                advisory_result["low_confidence_warning"]
            ),

            "pesticide_safety_disclaimer": (
                advisory_result["pesticide_safety_disclaimer"]
            ),

            "sources": (
                advisory_result["sources"]
            ),

            "engine": (
                advisory_result["engine"]
            )
        })

    else:

        response["advisory"]["error"] = advisory_error

    # --------------------------------------------------------
    # Evidence (knowledge-layer support for the advisory)
    # --------------------------------------------------------

    if advisory_record:

        response["advisory"]["evidence"] = (
            _build_evidence_for_report(
                db,
                health_report.id
            )
        )

    return response


# ============================================================
# GET HEALTH REPORT
# ============================================================

@app.get("/health-reports/{report_id}")
def get_health_report(
    report_id: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Find health report
    # --------------------------------------------------------

    health_report = (
        db.query(HealthReport)
        .filter(HealthReport.id == report_id)
        .first()
    )

    if not health_report:

        raise HTTPException(
            status_code=404,
            detail="Health report not found."
        )

    # --------------------------------------------------------
    # Find farm
    # --------------------------------------------------------

    farm = (
        db.query(Farm)
        .filter(Farm.id == health_report.farm_id)
        .first()
    )

    # --------------------------------------------------------
    # Find farmer
    # --------------------------------------------------------

    farmer = None

    if farm:

        farmer = (
            db.query(Farmer)
            .filter(Farmer.id == farm.farmer_id)
            .first()
        )

    # --------------------------------------------------------
    # Find crop season
    # --------------------------------------------------------

    crop_season = (
        db.query(CropSeason)
        .filter(
            CropSeason.id == health_report.crop_season_id
        )
        .first()
    )

    # --------------------------------------------------------
    # Find crop
    # --------------------------------------------------------

    crop = None

    if crop_season:

        crop = (
            db.query(Crop)
            .filter(Crop.id == crop_season.crop_id)
            .first()
        )

    # --------------------------------------------------------
    # Find linked image
    # --------------------------------------------------------

    image_record = (
        db.query(Image)
        .filter(
            Image.health_report_id == health_report.id
        )
        .order_by(desc(Image.created_at))
        .first()
    )

    # --------------------------------------------------------
    # Find AI prediction
    # --------------------------------------------------------

    prediction_record = (
        db.query(AIPrediction)
        .filter(
            AIPrediction.health_report_id == health_report.id
        )
        .order_by(desc(AIPrediction.created_at))
        .first()
    )

    # --------------------------------------------------------
    # Find weather
    # --------------------------------------------------------

    weather_record = (
        db.query(WeatherRecord)
        .filter(
            WeatherRecord.health_report_id == health_report.id
        )
        .order_by(desc(WeatherRecord.created_at))
        .first()
    )

    # --------------------------------------------------------
    # Find risk assessment
    # --------------------------------------------------------

    risk_record = (
        db.query(RiskAssessment)
        .filter(
            RiskAssessment.health_report_id == health_report.id
        )
        .order_by(desc(RiskAssessment.created_at))
        .first()
    )

    # --------------------------------------------------------
    # Find advisory
    # --------------------------------------------------------

    advisory_record = (
        db.query(Advisory)
        .filter(
            Advisory.health_report_id == health_report.id
        )
        .order_by(desc(Advisory.created_at))
        .first()
    )

    # --------------------------------------------------------
    # Build response
    # --------------------------------------------------------

    response = {

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

        "farmer": None,

        "farm": None,

        "crop_season": None,

        "crop": None,

        "image": None,

        "prediction": None,

        "weather": None,

        "risk": None,

        "advisory": None,

        "monitoring": {
            "is_follow_up": False,
            "original_report_id": None,
            "follow_up_id": None
        },

        "escalation": None,

        "expert_validations": []
    }

    # --------------------------------------------------------
    # Farmer
    # --------------------------------------------------------

    if farmer:

        response["farmer"] = {
            "id": farmer.id,
            "name": farmer.name,
            "phone": farmer.phone,
            "email": farmer.email,
            "preferred_language": farmer.preferred_language
        }

    # --------------------------------------------------------
    # Farm
    # --------------------------------------------------------

    if farm:

        response["farm"] = {
            "id": farm.id,
            "farmer_id": farm.farmer_id,
            "farm_name": farm.farm_name,
            "latitude": farm.latitude,
            "longitude": farm.longitude,
            "district": farm.district,
            "state": farm.state,
            "country": farm.country,
            "area_hectares": farm.area_hectares
        }

    # --------------------------------------------------------
    # Crop season
    # --------------------------------------------------------

    if crop_season:

        response["crop_season"] = {
            "id": crop_season.id,
            "farm_id": crop_season.farm_id,
            "crop_id": crop_season.crop_id,
            "variety": crop_season.variety,
            "planting_date": crop_season.planting_date,
            "expected_harvest_date": (
                crop_season.expected_harvest_date
            ),
            "stage_id": crop_season.stage_id,
            "status": crop_season.status
        }

    # --------------------------------------------------------
    # Crop
    # --------------------------------------------------------

    if crop:

        response["crop"] = {
            "id": crop.id,
            "name": crop.name,
            "scientific_name": crop.scientific_name,
            "category": crop.category,
            "description": crop.description,
            "is_active": crop.is_active
        }

    # --------------------------------------------------------
    # Image
    # --------------------------------------------------------

    if image_record:

        response["image"] = {
            "id": image_record.id,
            "health_report_id": image_record.health_report_id,
            "file_name": image_record.file_name,
            "file_size": image_record.file_size,
            "mime_type": image_record.mime_type,
            "storage_path": image_record.storage_path,
            "captured_at": image_record.captured_at,
            "created_at": image_record.created_at
        }

    # --------------------------------------------------------
    # AI prediction
    # --------------------------------------------------------

    if prediction_record:

        response["prediction"] = {
            "id": prediction_record.id,
            "model_name": prediction_record.model_name,
            "model_version": prediction_record.model_version,
            "prediction_type": prediction_record.prediction_type,
            "predicted_class": prediction_record.predicted_class,
            "confidence": prediction_record.confidence,
            "prediction_data": prediction_record.prediction_data,
            "created_at": prediction_record.created_at
        }

    # --------------------------------------------------------
    # Weather
    #
    # IMPORTANT:
    # raw_data remains stored in PostgreSQL but is not returned
    # by the normal farmer-facing detailed endpoint.
    # --------------------------------------------------------

    if weather_record:

        response["weather"] = {
            "id": weather_record.id,
            "health_report_id": weather_record.health_report_id,
            "latitude": weather_record.latitude,
            "longitude": weather_record.longitude,
            "temperature": weather_record.temperature,
            "humidity": weather_record.humidity,
            "rainfall": weather_record.rainfall,
            "rain_probability": weather_record.rain_probability,
            "wind_speed": weather_record.wind_speed,
            "weather_condition": weather_record.weather_condition,
            "observed_at": weather_record.observed_at,
            "provider": weather_record.provider,
            "created_at": weather_record.created_at
        }

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    if risk_record:

        response["risk"] = {
            "id": risk_record.id,
            "health_report_id": risk_record.health_report_id,
            "risk_score": risk_record.risk_score,
            "risk_level": risk_record.risk_level,
            "calculation_method": risk_record.calculation_method,
            "factors": risk_record.factors,
            "created_at": risk_record.created_at
        }

    # --------------------------------------------------------
    # Advisory
    # --------------------------------------------------------

    if advisory_record:

        response["advisory"] = {
            "id": advisory_record.id,
            "health_report_id": advisory_record.health_report_id,
            "language": advisory_record.language,
            "risk_level": advisory_record.risk_level,
            "advisory_text": advisory_record.advisory_text,
            "model_name": advisory_record.model_name,
            "model_version": advisory_record.model_version,
            "sources": advisory_record.sources,
            "created_at": advisory_record.created_at,
            "evidence": _build_evidence_for_report(
                db,
                health_report.id
            )
        }

    # --------------------------------------------------------
    # Monitoring relationship
    # --------------------------------------------------------

    follow_up_as_original = (
        db.query(FollowUp)
        .filter(
            FollowUp.original_report_id == health_report.id
        )
        .order_by(desc(FollowUp.id))
        .first()
    )

    follow_up_as_completed = (
        db.query(FollowUp)
        .filter(
            FollowUp.follow_up_report_id == health_report.id
        )
        .order_by(desc(FollowUp.id))
        .first()
    )

    if follow_up_as_completed:

        response["monitoring"] = {
            "is_follow_up": True,
            "original_report_id": (
                follow_up_as_completed.original_report_id
            ),
            "follow_up_id": follow_up_as_completed.id
        }

    elif follow_up_as_original:

        response["monitoring"] = {
            "is_follow_up": False,
            "original_report_id": None,
            "follow_up_id": follow_up_as_original.id
        }

    # --------------------------------------------------------
    # Escalation decision
    # --------------------------------------------------------

    escalation_comparison = None

    if follow_up_as_completed:

        original_snapshot = _build_report_snapshot(
            db,
            follow_up_as_completed.original_report_id
        )

        current_snapshot = _build_report_snapshot(
            db,
            health_report.id
        )

        if original_snapshot and current_snapshot:

            escalation_comparison = compare_reports(
                original_report=original_snapshot,
                follow_up_report=current_snapshot
            )

    response["escalation"] = _build_escalation(
        db,
        health_report.id,
        comparison=escalation_comparison
    )

    # --------------------------------------------------------
    # Explanation (optional natural-language layer)
    # --------------------------------------------------------

    response["explanation"] = _build_explanation_for_report(
        db,
        health_report.id
    )
    response["expert_validations"] = (_build_expert_validations_for_report(db, health_report.id))

    return response

# ============================================================
# FARM HEALTH HISTORY
# ============================================================

@app.get("/farms/{farm_id}/health-reports")
def get_farm_health_history(
    farm_id: int,
    db: Session = Depends(get_db)
):

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
    # Get reports
    # --------------------------------------------------------

    reports = (
        db.query(HealthReport)
        .filter(
            HealthReport.farm_id == farm_id
        )
        .order_by(
            desc(HealthReport.reported_at)
        )
        .all()
    )

    history = []

    for report in reports:

        crop_season = (
            db.query(CropSeason)
            .filter(
                CropSeason.id == report.crop_season_id
            )
            .first()
        )

        crop = None

        if crop_season:

            crop = (
                db.query(Crop)
                .filter(
                    Crop.id == crop_season.crop_id
                )
                .first()
            )

        prediction_record = (
            db.query(AIPrediction)
            .filter(
                AIPrediction.health_report_id == report.id
            )
            .order_by(
                desc(AIPrediction.created_at)
            )
            .first()
        )

        risk_record = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.health_report_id == report.id
            )
            .order_by(
                desc(RiskAssessment.created_at)
            )
            .first()
        )

        advisory_record = (
            db.query(Advisory)
            .filter(
                Advisory.health_report_id == report.id
            )
            .order_by(
                desc(Advisory.created_at)
            )
            .first()
        )

        history.append({

            "health_report_id": report.id,

            "reported_at": report.reported_at,

            "crop_season_id": report.crop_season_id,

            "crop": (
                crop.name
                if crop
                else None
            ),

            "variety": (
                crop_season.variety
                if crop_season
                else None
            ),

            "status": report.status,

            "prediction": (
                {
                    "disease": prediction_record.predicted_class,
                    "confidence": prediction_record.confidence
                }
                if prediction_record
                else None
            ),

            "risk": (
                {
                    "score": risk_record.risk_score,
                    "level": risk_record.risk_level
                }
                if risk_record
                else None
            ),

            "advisory": (
                {
                    "id": advisory_record.id,
                    "risk_level": advisory_record.risk_level
                }
                if advisory_record
                else None
            )
        })

    return {

        "farm": {
            "id": farm.id,
            "farmer_id": farm.farmer_id,
            "farm_name": farm.farm_name,
            "district": farm.district,
            "state": farm.state
        },

        "total_reports": len(history),

        "reports": history
    }


# ============================================================
# CREATE FOLLOW-UP
# ============================================================

@app.post("/health-reports/{report_id}/follow-up")
def create_follow_up(
    report_id: int,
    follow_up: FollowUpCreate,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Find original report
    # --------------------------------------------------------

    original_report = (
        db.query(HealthReport)
        .filter(
            HealthReport.id == report_id
        )
        .first()
    )

    if not original_report:

        raise HTTPException(
            status_code=404,
            detail="Original health report not found."
        )

    # --------------------------------------------------------
    # Prevent duplicate pending follow-ups
    # --------------------------------------------------------

    existing_pending = (
        db.query(FollowUp)
        .filter(
            FollowUp.original_report_id == report_id,
            FollowUp.status == "PENDING"
        )
        .first()
    )

    if existing_pending:

        raise HTTPException(
            status_code=400,
            detail=(
                "A pending follow-up already exists "
                "for this health report."
            )
        )

    # --------------------------------------------------------
    # Create follow-up
    # --------------------------------------------------------

    new_follow_up = FollowUp(
        original_report_id=report_id,
        scheduled_date=follow_up.scheduled_date,
        status="PENDING",
        farmer_notes=follow_up.farmer_notes
    )

    db.add(new_follow_up)

    try:

        db.commit()

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database operation failed: {str(e)}"
        )

    db.refresh(new_follow_up)

    return {

        "message": "Follow-up scheduled successfully",

        "follow_up": {
            "id": new_follow_up.id,

            "original_report_id": (
                new_follow_up.original_report_id
            ),

            "follow_up_report_id": (
                new_follow_up.follow_up_report_id
            ),

            "scheduled_date": (
                new_follow_up.scheduled_date
            ),

            "completed_at": (
                new_follow_up.completed_at
            ),

            "status": new_follow_up.status,

            "farmer_notes": (
                new_follow_up.farmer_notes
            )
        }
    }


# ============================================================
# GET FOLLOW-UPS FOR A REPORT
# ============================================================

@app.get("/health-reports/{report_id}/follow-ups")
def get_report_follow_ups(
    report_id: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Validate report
    # --------------------------------------------------------

    report = (
        db.query(HealthReport)
        .filter(
            HealthReport.id == report_id
        )
        .first()
    )

    if not report:

        raise HTTPException(
            status_code=404,
            detail="Health report not found."
        )

    # --------------------------------------------------------
    # Find follow-ups created from this report
    # --------------------------------------------------------

    follow_ups = (
        db.query(FollowUp)
        .filter(
            FollowUp.original_report_id == report_id
        )
        .order_by(
            desc(FollowUp.id)
        )
        .all()
    )

    results = []

    for follow_up in follow_ups:

        follow_up_report = None

        if follow_up.follow_up_report_id:

            follow_up_report = (
                db.query(HealthReport)
                .filter(
                    HealthReport.id ==
                    follow_up.follow_up_report_id
                )
                .first()
            )

        follow_up_summary = None

        if follow_up_report:

            prediction_record = (
                db.query(AIPrediction)
                .filter(
                    AIPrediction.health_report_id ==
                    follow_up_report.id
                )
                .order_by(
                    desc(AIPrediction.created_at)
                )
                .first()
            )

            risk_record = (
                db.query(RiskAssessment)
                .filter(
                    RiskAssessment.health_report_id ==
                    follow_up_report.id
                )
                .order_by(
                    desc(RiskAssessment.created_at)
                )
                .first()
            )

            follow_up_summary = {

                "health_report_id": (
                    follow_up_report.id
                ),

                "reported_at": (
                    follow_up_report.reported_at
                ),

                "status": (
                    follow_up_report.status
                ),

                "prediction": (
                    {
                        "disease":
                            prediction_record.predicted_class,
                        "confidence":
                            prediction_record.confidence
                    }
                    if prediction_record
                    else None
                ),

                "risk": (
                    {
                        "score":
                            risk_record.risk_score,
                        "level":
                            risk_record.risk_level
                    }
                    if risk_record
                    else None
                )
            }

        # ----------------------------------------------------
        # Deterministic comparison (only when follow-up
        # report is actually linked)
        # ----------------------------------------------------

        comparison = None

        if follow_up_report:

            original_snapshot = _build_report_snapshot(
                db,
                follow_up.original_report_id
            )

            follow_up_snapshot = _build_report_snapshot(
                db,
                follow_up_report.id
            )

            if original_snapshot and follow_up_snapshot:

                comparison = compare_reports(
                    original_report=original_snapshot,
                    follow_up_report=follow_up_snapshot
                )

        # ----------------------------------------------------
        # Escalation decision (only when follow-up report
        # is actually linked)
        # ----------------------------------------------------

        escalation = None

        if follow_up_report:

            escalation = _build_escalation(
                db,
                follow_up_report.id,
                comparison=comparison
            )

        results.append({

            "id": follow_up.id,

            "original_report_id":
                follow_up.original_report_id,

            "follow_up_report_id":
                follow_up.follow_up_report_id,

            "scheduled_date":
                follow_up.scheduled_date,

            "completed_at":
                follow_up.completed_at,

            "status":
                follow_up.status,

            "farmer_notes":
                follow_up.farmer_notes,

            "follow_up_report":
                follow_up_summary,

            "comparison":
                comparison,

            "escalation":
                escalation
        })

    return {

        "original_report_id": report_id,

        "total_follow_ups": len(results),

        "follow_ups": results
    }


# ============================================================
# MONITORING COMPARISON
# ============================================================

@app.get("/health-reports/{report_id}/comparison")
def get_health_report_comparison(
    report_id: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Validate report
    # --------------------------------------------------------

    report = (
        db.query(HealthReport)
        .filter(HealthReport.id == report_id)
        .first()
    )

    if not report:

        raise HTTPException(
            status_code=404,
            detail="Health report not found."
        )

    # --------------------------------------------------------
    # Determine which side is original and which is follow-up
    #
    # A report can be either:
    #   - the original side of a completed follow-up
    #   - the follow-up side linked back to an original
    #
    # The endpoint works from either side.
    # --------------------------------------------------------

    follow_up_as_original = (
        db.query(FollowUp)
        .filter(
            FollowUp.original_report_id == report_id,
            FollowUp.status == "COMPLETED",
            FollowUp.follow_up_report_id.isnot(None)
        )
        .order_by(desc(FollowUp.id))
        .first()
    )

    follow_up_as_completed = (
        db.query(FollowUp)
        .filter(FollowUp.follow_up_report_id == report_id)
        .order_by(desc(FollowUp.id))
        .first()
    )

    original_report_id = None
    follow_up_report_id = None

    if follow_up_as_original:

        original_report_id = follow_up_as_original.original_report_id
        follow_up_report_id = follow_up_as_original.follow_up_report_id

    elif follow_up_as_completed:

        original_report_id = follow_up_as_completed.original_report_id
        follow_up_report_id = follow_up_as_completed.follow_up_report_id

    if original_report_id is None or follow_up_report_id is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No completed follow-up is linked to this "
                "health report yet."
            )
        )

    # --------------------------------------------------------
    # Build snapshots
    # --------------------------------------------------------
    _validate_comparison_linkage(
        db,
        original_report_id,
        follow_up_report_id
    )
    original_snapshot = _build_report_snapshot(
        db,
        original_report_id
    )

    follow_up_snapshot = _build_report_snapshot(
        db,
        follow_up_report_id
    )

    if not original_snapshot or not follow_up_snapshot:

        raise HTTPException(
            status_code=404,
            detail=(
                "One of the linked health reports could not "
                "be loaded."
            )
        )

    # --------------------------------------------------------
    # Deterministic comparison
    # --------------------------------------------------------

    comparison = compare_reports(
        original_report=original_snapshot,
        follow_up_report=follow_up_snapshot
    )

    # --------------------------------------------------------
    # Escalation decision on the follow-up side
    # --------------------------------------------------------

    escalation = _build_escalation(
        db,
        follow_up_report_id,
        comparison=comparison
    )

    return {

        "original_report_id": original_report_id,
        "follow_up_report_id": follow_up_report_id,

        "comparison": comparison,

        "escalation": escalation
    }



# ============================================================
# EXPERT VALIDATION
# ============================================================

@app.post("/health-reports/{report_id}/expert-validation")
def create_expert_validation(
    report_id: int,
    payload: ExpertValidationCreate,
    db: Session = Depends(get_db)
):

    result = validate_submission(
        db=db,
        health_report_id=report_id,
        status=payload.status,
        confirmed_condition_name=payload.confirmed_condition,
    )

    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])

    expert = (
        db.query(Farmer)
        .filter(Farmer.id == payload.expert_id)
        .first()
    )

    if not expert:
        raise HTTPException(status_code=404, detail="Expert (farmer) not found.")

    confirmed_condition = result["confirmed_condition"]

    validation = ExpertValidation(
        health_report_id=report_id,
        expert_id=payload.expert_id,
        confirmed_condition_id=(
            confirmed_condition.id if confirmed_condition else None
        ),
        status=result["status"],
        comments=payload.comments,
    )

    db.add(validation)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database operation failed: {str(e)}",
        )

    db.refresh(validation)

    return {
        "message": "Expert validation recorded.",
        "validation": serialize_validation(db, validation),
    }


@app.get("/health-reports/{report_id}/expert-validation")
def get_expert_validations(
    report_id: int,
    db: Session = Depends(get_db)
):

    report = (
        db.query(HealthReport)
        .filter(HealthReport.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail="Health report not found.")

    validations = _build_expert_validations_for_report(db, report_id)

    return {
        "health_report_id": report_id,
        "total_validations": len(validations),
        "validations": validations,
    }


# ============================================================
# EXPERT REVIEW QUEUE
# ============================================================

@app.get("/expert-review/queue")
def get_expert_review_queue(
    district: str | None = None,
    limit: int = 50,
    include_reviewed: bool = False,
    db: Session = Depends(get_db)
):
    return build_review_queue(
        db=db,
        district=district,
        limit=limit,
        include_reviewed=include_reviewed,
    )

# ============================================================
# GEOSPATIAL HOTSPOTS
# ============================================================

@app.get("/hotspots")
def get_hotspots(
    condition: str | None = None,
    days: int = 14,
    radius_km: float = 5.0,
    min_reports: int = 3,
    district: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Return all active hotspot clusters.

    A hotspot is a group of >= min_reports reports of the same
    condition within radius_km of each other, within the last
    `days` days.

    Computed live. Nothing is persisted.
    """

    hotspots = find_hotspots(
        db=db,
        condition=condition,
        days=days,
        radius_km=radius_km,
        min_reports=min_reports,
        district=district,
    )

    return {
        "filters": {
            "condition": condition,
            "days": days,
            "radius_km": radius_km,
            "min_reports": min_reports,
            "district": district,
        },
        "total_hotspots": len(hotspots),
        "hotspots": hotspots,
    }


@app.get("/hotspots/near")
def get_hotspots_near(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    days: int = 14,
    min_reports: int = 3,
    db: Session = Depends(get_db)
):
    """
    Return hotspots whose cluster center is within radius_km
    of the given point.

    Useful for a "what's happening around my farm" panel.
    """

    hotspots = find_hotspots(
        db=db,
        days=days,
        radius_km=radius_km,
        min_reports=min_reports,
    )

    # Filter to hotspots whose center is within the search radius
    from hotspots import haversine_km

    nearby = []

    for hotspot in hotspots:

        center = hotspot["center"]

        distance = haversine_km(
            latitude,
            longitude,
            center["latitude"],
            center["longitude"],
        )

        if distance <= radius_km:

            hotspot_with_distance = dict(hotspot)
            hotspot_with_distance["distance_from_query_km"] = round(
                distance, 2
            )

            nearby.append(hotspot_with_distance)

    nearby.sort(key=lambda h: h["distance_from_query_km"])

    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km,
            "days": days,
            "min_reports": min_reports,
        },
        "total_hotspots": len(nearby),
        "hotspots": nearby,
    }