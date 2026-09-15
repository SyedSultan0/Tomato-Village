from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

# ============================================================
# DATABASE CONNECTION
# ============================================================

DATABASE_URL = "postgresql://postgres:sultan@localhost:5432/sih_crop_health"

engine = create_engine(DATABASE_URL)

Base = declarative_base()

from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
# ============================================================
# 1. FARMERS
# ============================================================

class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True)
    email = Column(String(150), unique=True)
    preferred_language = Column(String(50), default="English")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# 2. FARMS
# ============================================================

class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)

    farm_name = Column(String(100))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    district = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="India")

    area_hectares = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# 3. CROPS
# ============================================================

class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    scientific_name = Column(String(150))
    category = Column(String(100))
    description = Column(Text)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 4. CROP SEASONS
# ============================================================

class CropSeason(Base):
    __tablename__ = "crop_seasons"

    id = Column(Integer, primary_key=True)

    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)

    variety = Column(String(100))

    planting_date = Column(Date)
    expected_harvest_date = Column(Date)

    stage_id = Column(Integer, ForeignKey("crop_stages.id"))

    status = Column(String(50), default="ACTIVE")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# 5. CROP STAGES
# ============================================================

class CropStage(Base):
    __tablename__ = "crop_stages"

    id = Column(Integer, primary_key=True)

    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)

    stage_name = Column(String(100), nullable=False)
    description = Column(Text)

    sequence_order = Column(Integer)


# ============================================================
# 6. CONDITIONS
#    Diseases + Pests
# ============================================================

class Condition(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True)

    name = Column(String(150), unique=True, nullable=False)

    condition_type = Column(String(50), nullable=False)
    # DISEASE / PEST / DEFICIENCY / OTHER

    description = Column(Text)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 7. CROP ↔ CONDITIONS
# ============================================================

class CropCondition(Base):
    __tablename__ = "crop_conditions"

    id = Column(Integer, primary_key=True)

    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False)
    condition_id = Column(Integer, ForeignKey("conditions.id"), nullable=False)

    susceptibility = Column(String(50))


# ============================================================
# 8. HEALTH REPORTS
# ============================================================

class HealthReport(Base):
    __tablename__ = "health_reports"

    id = Column(Integer, primary_key=True)

    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    crop_season_id = Column(
        Integer,
        ForeignKey("crop_seasons.id"),
        nullable=False
    )

    latitude = Column(Float)
    longitude = Column(Float)

    source = Column(String(50), default="FARMER")
    # FARMER / EXPERT / SENSOR / ADMIN

    status = Column(String(50), default="PENDING")

    notes = Column(Text)

    reported_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 9. IMAGES
# ============================================================

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    image_url = Column(Text)
    storage_path = Column(Text)
    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))

    captured_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 10. AI PREDICTIONS
# ============================================================

class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    model_name = Column(String(100))
    model_version = Column(String(100))

    prediction_type = Column(String(50))
    # CLASSIFICATION / DETECTION / MULTILABEL

    predicted_class = Column(String(150))

    confidence = Column(Float)

    prediction_data = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 11. WEATHER RECORDS
# ============================================================

# ============================================================
# 11. WEATHER RECORDS
#     Weather + Agricultural Environment Data
# ============================================================

class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    latitude = Column(Float)
    longitude = Column(Float)

    # Important normalized weather values
    temperature = Column(Float)
    humidity = Column(Float)
    rainfall = Column(Float)
    rain_probability = Column(Float)
    wind_speed = Column(Float)
    weather_condition = Column(String(100))

    # Complete Open-Meteo response
    # This lets us preserve additional weather/environmental
    # variables for future risk calculations.
    raw_data = Column(JSON)

    observed_at = Column(DateTime)
    provider = Column(String(100))

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
# ============================================================
# 12. RISK ASSESSMENTS
# ============================================================

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    risk_score = Column(Float)
    risk_level = Column(String(50))

    calculation_method = Column(String(100))

    factors = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 13. DISEASE/PEST CASES
# ============================================================

class DiseaseCase(Base):
    __tablename__ = "disease_cases"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    condition_id = Column(
        Integer,
        ForeignKey("conditions.id"),
        nullable=False
    )

    latitude = Column(Float)
    longitude = Column(Float)

    severity = Column(String(50))
    status = Column(String(50))

    detected_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 14. EXPERT VALIDATIONS
# ============================================================

class ExpertValidation(Base):
    __tablename__ = "expert_validations"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    expert_id = Column(Integer, ForeignKey("farmers.id"))

    confirmed_condition_id = Column(
        Integer,
        ForeignKey("conditions.id")
    )

    status = Column(String(50), nullable=False)

    comments = Column(Text)

    validated_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 15. FOLLOW-UPS
# ============================================================

class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True)

    original_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    follow_up_report_id = Column(
        Integer,
        ForeignKey("health_reports.id")
    )

    scheduled_date = Column(Date)

    completed_at = Column(DateTime)

    status = Column(String(50), default="PENDING")

    farmer_notes = Column(Text)


# ============================================================
# 16. SENSORS
# ============================================================

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True)

    farm_id = Column(
        Integer,
        ForeignKey("farms.id"),
        nullable=False
    )

    sensor_type = Column(String(100))

    device_identifier = Column(String(150), unique=True)

    location_latitude = Column(Float)
    location_longitude = Column(Float)

    status = Column(String(50), default="ACTIVE")

    installed_at = Column(DateTime)


# ============================================================
# 17. SENSOR READINGS
# ============================================================

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)

    sensor_id = Column(
        Integer,
        ForeignKey("sensors.id"),
        nullable=False
    )

    reading_type = Column(String(100))

    value = Column(Float)

    unit = Column(String(50))

    recorded_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 18. KNOWLEDGE DOCUMENTS
# ============================================================

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True)

    title = Column(String(255), nullable=False)

    source = Column(Text)
    source_type = Column(String(100))

    crop_id = Column(Integer, ForeignKey("crops.id"))
    condition_id = Column(Integer, ForeignKey("conditions.id"))

    language = Column(String(50), default="English")

    version = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# 19. KNOWLEDGE CHUNKS
# ============================================================

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True)

    document_id = Column(
        Integer,
        ForeignKey("knowledge_documents.id"),
        nullable=False
    )

    chunk_text = Column(Text, nullable=False)

    chunk_index = Column(Integer)

    chunk_metadata = Column(JSON)

    embedding_reference = Column(String(255))

    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================================
# 20. ADVISORIES
# ============================================================

class Advisory(Base):
    __tablename__ = "advisories"

    id = Column(Integer, primary_key=True)

    health_report_id = Column(
        Integer,
        ForeignKey("health_reports.id"),
        nullable=False
    )

    language = Column(String(50), default="English")

    risk_level = Column(String(50))

    advisory_text = Column(Text)

    model_name = Column(String(100))
    model_version = Column(String(100))

    sources = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# CREATE ALL TABLES
# ============================================================

if __name__ == "__main__":
    print("Creating database tables...")

    Base.metadata.create_all(engine)

    print("✅ All database tables created successfully!")