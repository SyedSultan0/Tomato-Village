from typing import Any
from datetime import datetime


# ============================================================
# RISK ENGINE
# ============================================================
#
# Transparent, rule-based environmental risk engine.
#
# AI MODEL:
#     Determines what condition is visible in the image.
#
# RISK ENGINE:
#     Estimates how favorable the current environmental
#     conditions are for that detected condition.
#
# This engine does NOT replace the AI diagnosis.
#
# Raw environmental score:
#     Normalized to 0 - 100 based on the maximum configured
#     environmental contribution for the detected condition.
#
# Final risk score:
#     Environmental score adjusted only mildly by AI confidence.
#
# Risk levels:
#     0 - 24    LOW
#     25 - 49   MODERATE
#     50 - 74   HIGH
#     75 - 100  CRITICAL
#
# Engine version:
#     rule-engine-v1
#
# The rules are intentionally transparent so that they can
# later be validated and refined using agricultural expert
# feedback and historical field outcomes.
# ============================================================


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0
):
    return max(
        minimum,
        min(maximum, value)
    )


def risk_level(score: float):
    if score < 25:
        return "LOW"

    if score < 50:
        return "MODERATE"

    if score < 75:
        return "HIGH"

    return "CRITICAL"


def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)

    except (ValueError, TypeError):
        return None


def average(values):
    valid_values = [
        value
        for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return sum(valid_values) / len(valid_values)


# ============================================================
# HOURLY TIMESTAMP SELECTION
# ============================================================

def find_relevant_hour_index(
    weather_data: dict[str, Any]
):
    """
    Find the hourly weather record closest to the current
    weather timestamp returned by Open-Meteo.

    Open-Meteo provides:
        current.time
        hourly.time[]

    We use the hourly record closest to current.time instead
    of assuming hourly index 0 is the relevant record.

    Returns:
        integer index or None
    """

    current = weather_data.get(
        "current",
        {}
    )

    hourly = weather_data.get(
        "hourly",
        {}
    )

    current_time = current.get(
        "time"
    )

    hourly_times = hourly.get(
        "time",
        []
    )

    if not hourly_times:
        return None

    # If current.time is unavailable, safely fall back
    # to the first available hourly record.
    if not current_time:
        return 0

    try:
        current_datetime = datetime.fromisoformat(
            current_time.replace(
                "Z",
                "+00:00"
            )
        )

    except (ValueError, TypeError):
        return 0

    closest_index = None
    smallest_difference = None

    for index, timestamp in enumerate(hourly_times):

        try:
            hourly_datetime = datetime.fromisoformat(
                timestamp.replace(
                    "Z",
                    "+00:00"
                )
            )

        except (ValueError, TypeError):
            continue

        difference = abs(
            (
                hourly_datetime -
                current_datetime
            ).total_seconds()
        )

        if (
            smallest_difference is None
            or difference < smallest_difference
        ):
            smallest_difference = difference
            closest_index = index

    return closest_index


# ============================================================
# EXTRACT WEATHER VALUES
# ============================================================

def extract_weather_values(
    weather_data: dict[str, Any]
):
    """
    Extract useful environmental values from the complete
    Open-Meteo response.

    Current atmospheric values come from the current object.

    Hourly variables such as:
        - precipitation probability
        - soil moisture
        - soil temperature

    are taken from the hourly record closest to the
    current weather timestamp.
    """

    current = weather_data.get(
        "current",
        {}
    )

    hourly = weather_data.get(
        "hourly",
        {}
    )

    values = {}

    # --------------------------------------------------------
    # Current atmospheric conditions
    # --------------------------------------------------------

    values["temperature"] = safe_float(
        current.get(
            "temperature_2m"
        )
    )

    values["humidity"] = safe_float(
        current.get(
            "relative_humidity_2m"
        )
    )

    values["dewpoint"] = safe_float(
        current.get(
            "dew_point_2m"
        )
    )

    values["rainfall"] = safe_float(
        current.get(
            "precipitation"
        )
    )

    values["wind_speed"] = safe_float(
        current.get(
            "wind_speed_10m"
        )
    )

    values["wind_gust"] = safe_float(
        current.get(
            "wind_gusts_10m"
        )
    )

    values["vpd"] = safe_float(
        current.get(
            "vapour_pressure_deficit"
        )
    )

    values["et0"] = safe_float(
        current.get(
            "et0_fao_evapotranspiration"
        )
    )

    values["cloud_cover"] = safe_float(
        current.get(
            "cloud_cover"
        )
    )

    values["solar_radiation"] = safe_float(
        current.get(
            "shortwave_radiation"
        )
    )

    values["current_time"] = current.get(
        "time"
    )

    # --------------------------------------------------------
    # Find correct hourly record
    # --------------------------------------------------------

    index = find_relevant_hour_index(
        weather_data
    )

    values["hourly_index"] = index

    if index is None:
        return values

    hourly_times = hourly.get(
        "time",
        []
    )

    if index < len(hourly_times):
        values["hourly_time"] = (
            hourly_times[index]
        )
    else:
        values["hourly_time"] = None

    # --------------------------------------------------------
    # Hourly helper
    # --------------------------------------------------------

    def hourly_value(name):
        data = hourly.get(
            name,
            []
        )

        if index >= len(data):
            return None

        return safe_float(
            data[index]
        )

    # --------------------------------------------------------
    # Precipitation probability
    # --------------------------------------------------------

    values["rain_probability"] = hourly_value(
        "precipitation_probability"
    )

    # --------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------

    values["soil_moisture_0_1cm"] = hourly_value(
        "soil_moisture_0_to_1cm"
    )

    values["soil_moisture_1_3cm"] = hourly_value(
        "soil_moisture_1_to_3cm"
    )

    values["soil_moisture_3_9cm"] = hourly_value(
        "soil_moisture_3_to_9cm"
    )

    # --------------------------------------------------------
    # Soil temperature
    # --------------------------------------------------------

    values["soil_temperature_0cm"] = hourly_value(
        "soil_temperature_0cm"
    )

    values["soil_temperature_6cm"] = hourly_value(
        "soil_temperature_6cm"
    )

    # --------------------------------------------------------
    # Useful averages
    # --------------------------------------------------------

    values["surface_soil_moisture"] = average([
        values.get(
            "soil_moisture_0_1cm"
        ),
        values.get(
            "soil_moisture_1_3cm"
        ),
        values.get(
            "soil_moisture_3_9cm"
        )
    ])

    values["soil_temperature_average"] = average([
        values.get(
            "soil_temperature_0cm"
        ),
        values.get(
            "soil_temperature_6cm"
        )
    ])

    return values


# ============================================================
# CONDITION PROFILES
# ============================================================
#
# Each profile defines the maximum contribution of each
# environmental factor.
#
# These are NOT disease probabilities.
#
# They are transparent risk-engine weights.
# ============================================================

CONDITION_PROFILES = {

    "late_blight": {
        "temperature": (15, 26, 25),
        "humidity": (85, 100, 25),
        "rain": 15,
        "rain_probability": 10,
        "vpd": 5,
        "wetness": 10,
        "description": (
            "Cool, humid and wet conditions favor late blight."
        )
    },

    "early_blight": {
        "temperature": (15, 30, 20),
        "humidity": (80, 100, 20),
        "rain": 15,
        "rain_probability": 8,
        "vpd": 3,
        "wetness": 10,
        "description": (
            "Warm, humid and wet conditions favor early blight."
        )
    },

    "leaf_miner": {
        "temperature": (20, 32, 18),
        "humidity": (45, 85, 8),
        "rain": 4,
        "rain_probability": 3,
        "vpd": 4,
        "wetness": 0,
        "description": (
            "Warm conditions can support insect activity."
        )
    },

    "spotted_wilt_virus": {
        "temperature": (20, 32, 10),
        "humidity": (40, 85, 5),
        "rain": 2,
        "rain_probability": 2,
        "vpd": 3,
        "wetness": 0,
        "description": (
            "Environmental conditions are secondary to "
            "vector pressure for spotted wilt."
        )
    },

    "magnesium_deficiency": {
        "temperature": (18, 35, 5),
        "humidity": (30, 90, 2),
        "rain": 3,
        "rain_probability": 2,
        "vpd": 8,
        "wetness": 0,
        "soil_moisture_stress": 10,
        "description": (
            "Environmental stress can influence nutrient "
            "availability and uptake, but soil testing is "
            "needed to confirm nutrient deficiency."
        )
    },

    "nitrogen_deficiency": {
        "temperature": (18, 35, 5),
        "humidity": (30, 90, 2),
        "rain": 3,
        "rain_probability": 2,
        "vpd": 8,
        "wetness": 0,
        "soil_moisture_stress": 10,
        "description": (
            "Water stress can reduce nutrient uptake, but "
            "weather alone cannot confirm nitrogen deficiency."
        )
    },

    "potassium_deficiency": {
        "temperature": (18, 35, 5),
        "humidity": (30, 90, 2),
        "rain": 3,
        "rain_probability": 2,
        "vpd": 8,
        "wetness": 0,
        "soil_moisture_stress": 10,
        "description": (
            "Environmental stress can affect nutrient uptake, "
            "but potassium deficiency requires further validation."
        )
    },

    "healthy": {
        "temperature": (0, 40, 0),
        "humidity": (0, 100, 0),
        "rain": 0,
        "rain_probability": 0,
        "vpd": 0,
        "wetness": 0,
        "soil_moisture_stress": 0,
        "description": (
            "No disease-specific environmental risk was detected."
        )
    }
}


# ============================================================
# TEMPERATURE SCORE
# ============================================================

def temperature_score(
    temperature,
    profile
):
    if temperature is None:
        return 0

    minimum, maximum, weight = profile

    if weight == 0:
        return 0

    if minimum <= temperature <= maximum:
        return weight

    distance = min(
        abs(temperature - minimum),
        abs(temperature - maximum)
    )

    if distance <= 5:
        return weight * 0.4

    return 0


# ============================================================
# HUMIDITY SCORE
# ============================================================

def humidity_score(
    humidity,
    minimum,
    maximum,
    weight
):
    if humidity is None or weight == 0:
        return 0

    if minimum <= humidity <= maximum:
        return weight

    if humidity < minimum:

        difference = minimum - humidity

        if difference <= 10:
            return weight * 0.5

        return 0

    difference = humidity - maximum

    if difference <= 10:
        return weight * 0.5

    return 0


# ============================================================
# RAIN SCORE
# ============================================================

def rain_score(
    rainfall,
    weight
):
    if rainfall is None or rainfall <= 0:
        return 0

    if rainfall >= 5:
        return weight

    if rainfall >= 2:
        return weight * 0.75

    return weight * 0.4


# ============================================================
# RAIN PROBABILITY SCORE
# ============================================================

def precipitation_probability_score(
    probability,
    weight
):
    if probability is None or weight == 0:
        return 0

    if probability >= 70:
        return weight

    if probability >= 40:
        return weight * 0.65

    if probability >= 20:
        return weight * 0.35

    return 0


# ============================================================
# VPD SCORE
# ============================================================

def vpd_score(
    vpd,
    weight
):
    if vpd is None or weight == 0:
        return 0

    # Lower VPD generally means greater atmospheric moisture.
    if vpd <= 0.4:
        return weight

    if vpd <= 0.8:
        return weight * 0.75

    if vpd <= 1.2:
        return weight * 0.35

    return 0


# ============================================================
# SOIL MOISTURE STRESS
# ============================================================

def soil_moisture_stress_score(
    soil_moisture,
    weight
):
    if soil_moisture is None or weight == 0:
        return 0

    # Conservative broad bands.
    #
    # Open-Meteo soil moisture is volumetric water content.
    # Exact dry/wet thresholds depend on soil texture,
    # field capacity and local conditions.
    #
    # Therefore these values are used only as broad
    # environmental stress signals.

    if soil_moisture < 0.12:
        return weight

    if soil_moisture < 0.18:
        return weight * 0.65

    if soil_moisture > 0.45:
        return weight * 0.4

    return 0


# ============================================================
# WETNESS SCORE
# ============================================================

def wetness_score(
    rainfall,
    humidity,
    rain_probability,
    weight
):
    """
    Estimate environmental wetness using multiple signals.

    This is intentionally NOT a leaf-wetness measurement.

    We combine:
        - recent precipitation
        - relative humidity
        - precipitation probability

    The factor is capped at its configured weight.
    """

    if weight == 0:
        return 0

    score = 0.0

    # Recent rain signal
    if rainfall is not None:

        if rainfall >= 5:
            score += weight * 0.45

        elif rainfall >= 2:
            score += weight * 0.30

        elif rainfall > 0:
            score += weight * 0.15

    # Humidity signal
    if humidity is not None:

        if humidity >= 90:
            score += weight * 0.35

        elif humidity >= 80:
            score += weight * 0.25

        elif humidity >= 70:
            score += weight * 0.10

    # Forecast precipitation signal
    if rain_probability is not None:

        if rain_probability >= 70:
            score += weight * 0.20

        elif rain_probability >= 40:
            score += weight * 0.12

        elif rain_probability >= 20:
            score += weight * 0.05

    return min(
        score,
        weight
    )


# ============================================================
# MAXIMUM PROFILE SCORE
# ============================================================

def maximum_profile_score(
    profile
):
    """
    Calculate the theoretical maximum environmental score
    configured for a condition.

    This allows different condition profiles to be normalized
    to the same 0 - 100 scale.
    """

    maximum = 0.0

    # Temperature
    temperature_profile = profile.get(
        "temperature",
        (0, 100, 0)
    )

    maximum += temperature_profile[2]

    # Humidity
    humidity_profile = profile.get(
        "humidity",
        (0, 100, 0)
    )

    maximum += humidity_profile[2]

    # Rain
    maximum += profile.get(
        "rain",
        0
    )

    # Rain probability
    maximum += profile.get(
        "rain_probability",
        0
    )

    # VPD
    maximum += profile.get(
        "vpd",
        0
    )

    # Wetness
    maximum += profile.get(
        "wetness",
        0
    )

    # Soil moisture stress
    maximum += profile.get(
        "soil_moisture_stress",
        0
    )

    return maximum


# ============================================================
# MAIN RISK CALCULATION
# ============================================================

def calculate_risk(
    disease: str,
    confidence: float,
    weather_data: dict
):
    """
    Calculate environmental risk for the AI-detected condition.

    Returns a transparent risk result containing:
        - normalized risk score
        - risk level
        - environmental score
        - AI confidence
        - contributing factors
        - weather snapshot
        - engine version
    """

    disease_key = (
        disease
        .lower()
        .strip()
    )

    profile = CONDITION_PROFILES.get(
        disease_key
    )

    # --------------------------------------------------------
    # Unknown condition
    # --------------------------------------------------------

    if profile is None:

        profile = {
            "temperature": (10, 35, 10),
            "humidity": (70, 100, 10),
            "rain": 10,
            "rain_probability": 5,
            "vpd": 5,
            "wetness": 5,
            "soil_moisture_stress": 5,
            "description": (
                "Generic environmental risk profile used because "
                "a condition-specific profile is not available."
            )
        }

    # --------------------------------------------------------
    # Extract weather
    # --------------------------------------------------------

    values = extract_weather_values(
        weather_data
    )

    factors = []

    raw_score = 0.0

    # --------------------------------------------------------
    # Temperature
    # --------------------------------------------------------

    temp_score = temperature_score(
        values.get("temperature"),
        profile["temperature"]
    )

    raw_score += temp_score

    if temp_score > 0:

        factors.append({
            "factor": "temperature",
            "value": values.get(
                "temperature"
            ),
            "contribution": round(
                temp_score,
                2
            ),
            "effect": "FAVORABLE"
        })

    # --------------------------------------------------------
    # Humidity
    # --------------------------------------------------------

    humidity_weight = profile.get(
        "humidity",
        (0, 100, 0)
    )

    humidity_score_value = humidity_score(
        values.get("humidity"),
        humidity_weight[0],
        humidity_weight[1],
        humidity_weight[2]
    )

    raw_score += humidity_score_value

    if humidity_score_value > 0:

        factors.append({
            "factor": "relative_humidity",
            "value": values.get(
                "humidity"
            ),
            "contribution": round(
                humidity_score_value,
                2
            ),
            "effect": "FAVORABLE"
        })

    # --------------------------------------------------------
    # Recent rain
    # --------------------------------------------------------

    rain_contribution = rain_score(
        values.get("rainfall"),
        profile.get(
            "rain",
            0
        )
    )

    raw_score += rain_contribution

    if rain_contribution > 0:

        factors.append({
            "factor": "recent_precipitation",
            "value": values.get(
                "rainfall"
            ),
            "contribution": round(
                rain_contribution,
                2
            ),
            "effect": "FAVORABLE"
        })

    # --------------------------------------------------------
    # Precipitation probability
    # --------------------------------------------------------

    probability_contribution = (
        precipitation_probability_score(
            values.get(
                "rain_probability"
            ),
            profile.get(
                "rain_probability",
                0
            )
        )
    )

    raw_score += probability_contribution

    if probability_contribution > 0:

        factors.append({
            "factor": "precipitation_probability",
            "value": values.get(
                "rain_probability"
            ),
            "contribution": round(
                probability_contribution,
                2
            ),
            "effect": "FAVORABLE"
        })

    # --------------------------------------------------------
    # VPD
    # --------------------------------------------------------

    vpd_contribution = vpd_score(
        values.get("vpd"),
        profile.get(
            "vpd",
            0
        )
    )

    raw_score += vpd_contribution

    if vpd_contribution > 0:

        factors.append({
            "factor": "vapour_pressure_deficit",
            "value": values.get(
                "vpd"
            ),
            "contribution": round(
                vpd_contribution,
                2
            ),
            "effect": "MOISTURE_FAVORABLE"
        })

    # --------------------------------------------------------
    # Wetness
    # --------------------------------------------------------

    wetness_weight = profile.get(
        "wetness",
        0
    )

    wetness_contribution = wetness_score(
        rainfall=values.get(
            "rainfall"
        ),
        humidity=values.get(
            "humidity"
        ),
        rain_probability=values.get(
            "rain_probability"
        ),
        weight=wetness_weight
    )

    raw_score += wetness_contribution

    if wetness_contribution > 0:

        factors.append({
            "factor": "environmental_wetness",
            "value": {
                "rainfall": values.get(
                    "rainfall"
                ),
                "humidity": values.get(
                    "humidity"
                ),
                "rain_probability": values.get(
                    "rain_probability"
                )
            },
            "contribution": round(
                wetness_contribution,
                2
            ),
            "effect": "WETNESS_FAVORABLE"
        })

    # --------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------

    soil_weight = profile.get(
        "soil_moisture_stress",
        0
    )

    soil_contribution = soil_moisture_stress_score(
        values.get(
            "surface_soil_moisture"
        ),
        soil_weight
    )

    raw_score += soil_contribution

    if soil_contribution > 0:

        factors.append({
            "factor": "surface_soil_moisture",
            "value": values.get(
                "surface_soil_moisture"
            ),
            "contribution": round(
                soil_contribution,
                2
            ),
            "effect": "STRESS_SIGNAL"
        })

    # --------------------------------------------------------
    # Normalize environmental score to 0 - 100
    # --------------------------------------------------------

    maximum_score = maximum_profile_score(
        profile
    )

    if maximum_score <= 0:

        environmental_score = 0.0

    else:

        environmental_score = clamp(
            (
                raw_score /
                maximum_score
            ) * 100
        )

    # --------------------------------------------------------
    # AI confidence modifier
    # --------------------------------------------------------
    #
    # Confidence does NOT dominate environmental risk.
    #
    # It only reduces risk slightly when the classifier
    # itself is uncertain.
    # --------------------------------------------------------

    confidence_value = safe_float(
        confidence
    )

    if confidence_value is None:
        confidence_value = 0.0

    confidence_value = clamp(
        confidence_value * 100
    )

    if confidence_value < 50:

        confidence_modifier = 0.75

    elif confidence_value < 70:

        confidence_modifier = 0.90

    else:

        confidence_modifier = 1.0

    final_score = clamp(
        environmental_score *
        confidence_modifier
    )

    level = risk_level(
        final_score
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    explanation = profile[
        "description"
    ]

    if not factors:

        explanation = (
            "No strong environmental risk factors were "
            "identified from the available weather data."
        )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {

        "risk_score": round(
            final_score,
            2
        ),

        "risk_level": level,

        "environmental_score": round(
            environmental_score,
            2
        ),

        "raw_environmental_score": round(
            raw_score,
            2
        ),

        "maximum_environmental_score": round(
            maximum_score,
            2
        ),

        "ai_confidence": round(
            confidence_value,
            2
        ),

        "condition": disease,

        "explanation": explanation,

        "factors": factors,

        "weather_snapshot": values,

        "engine_version": "rule-engine-v1"
    }