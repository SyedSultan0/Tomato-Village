import json
import re
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ADVISORY_DATA_FILE = BASE_DIR / "advisory_data.json"

SUPPORTED_RISK_LEVELS = {
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
}

LOW_CONFIDENCE_THRESHOLD = 0.70


# ============================================================
# LOAD ADVISORY DATA
# ============================================================

def _load_advisory_data() -> dict[str, Any]:
    """
    Load the deterministic advisory source-of-truth JSON.

    The file is loaded once when this module starts.
    """

    if not ADVISORY_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Advisory data file not found: {ADVISORY_DATA_FILE}"
        )

    with open(ADVISORY_DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data


ADVISORY_DATA = _load_advisory_data()


# ============================================================
# VALIDATION
# ============================================================

def _validate_advisory_data() -> None:
    """
    Validate the advisory dataset when the backend starts.

    Expected:
        8 conditions
        4 risk levels per condition
        32 total advisory combinations
    """

    if "advisories" not in ADVISORY_DATA:
        raise ValueError("advisory_data.json is missing 'advisories'.")

    if "global" not in ADVISORY_DATA:
        raise ValueError("advisory_data.json is missing 'global'.")

    advisories = ADVISORY_DATA["advisories"]

    if not isinstance(advisories, list):
        raise ValueError("'advisories' must be a list.")

    seen_conditions = set()

    for advisory in advisories:
        required_fields = [
            "condition_id",
            "model_label",
            "category",
            "risk_levels",
        ]

        for field in required_fields:
            if field not in advisory:
                raise ValueError(
                    f"Advisory '{advisory}' is missing '{field}'."
                )

        condition_id = advisory["condition_id"]

        if condition_id in seen_conditions:
            raise ValueError(
                f"Duplicate condition_id found: {condition_id}"
            )

        seen_conditions.add(condition_id)

        risk_levels = advisory["risk_levels"]

        if not isinstance(risk_levels, dict):
            raise ValueError(
                f"risk_levels for '{condition_id}' must be an object."
            )

        missing_levels = SUPPORTED_RISK_LEVELS - set(risk_levels.keys())

        if missing_levels:
            raise ValueError(
                f"Condition '{condition_id}' is missing risk levels: "
                f"{sorted(missing_levels)}"
            )

        for risk_level in SUPPORTED_RISK_LEVELS:
            entry = risk_levels[risk_level]

            required_entry_fields = [
                "summary",
                "immediate_actions",
                "prevention",
                "monitoring",
                "expert_referral",
            ]

            for field in required_entry_fields:
                if field not in entry:
                    raise ValueError(
                        f"{condition_id}/{risk_level} is missing '{field}'."
                    )

    total_combinations = len(advisories) * len(SUPPORTED_RISK_LEVELS)

    if total_combinations != 32:
        raise ValueError(
            f"Expected 32 advisory combinations, "
            f"found {total_combinations}."
        )


_validate_advisory_data()


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_model_label(model_label: str) -> str:
    """
    Normalize the model's output so lookup is robust.

    Example:
        'Late Blight'
        'late blight'
        'Late_Blight'

    all become:
        'late blight'
    """

    if not isinstance(model_label, str):
        raise ValueError("model_label must be a string.")

    normalized = model_label.strip().lower()
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized


def _normalize_risk_level(risk_level: str) -> str:
    """
    Normalize Risk Engine output.
    """

    if not isinstance(risk_level, str):
        raise ValueError("risk_level must be a string.")

    normalized = risk_level.strip().upper()

    if normalized not in SUPPORTED_RISK_LEVELS:
        raise ValueError(
            f"Unsupported risk level: {risk_level}. "
            f"Expected one of {sorted(SUPPORTED_RISK_LEVELS)}."
        )

    return normalized


# ============================================================
# ADVISORY LOOKUP
# ============================================================

def _find_condition(model_label: str) -> dict[str, Any]:
    """
    Find the condition definition using the model label.
    """

    normalized_label = _normalize_model_label(model_label)

    for advisory in ADVISORY_DATA["advisories"]:
        advisory_label = _normalize_model_label(
            advisory["model_label"]
        )

        if advisory_label == normalized_label:
            return advisory

    raise ValueError(
        f"No advisory found for model label: '{model_label}'."
    )


def _get_advisory_entry(
    model_label: str,
    risk_level: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Perform the core deterministic lookup:

        model_label + risk_level
                    ↓
               advisory row
    """

    condition = _find_condition(model_label)
    normalized_risk = _normalize_risk_level(risk_level)

    risk_entry = condition["risk_levels"][normalized_risk]

    return condition, risk_entry


# ============================================================
# WEATHER HELPERS
# ============================================================

def _get_numeric(
    data: dict[str, Any],
    *keys: str,
) -> float | None:
    """
    Safely retrieve a numeric value from a weather dictionary.

    Supports alternate field names because the Risk Engine's
    weather snapshot may evolve.
    """

    for key in keys:
        value = data.get(key)

        if value is None:
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return None


def _extract_weather_snapshot(
    weather_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Normalize the weather snapshot passed from Risk Engine.

    This function does not calculate risk.
    It only extracts values needed by advisory modifiers.
    """

    if not weather_snapshot:
        return {}

    snapshot = weather_snapshot.copy()

    temperature = _get_numeric(
        snapshot,
        "temperature",
        "temperature_2m",
        "current_temperature",
    )

    dew_point = _get_numeric(
        snapshot,
        "dew_point",
        "dewpoint",
        "dew_point_2m",
    )

    wind_speed = _get_numeric(
        snapshot,
        "wind_speed",
        "wind_speed_10m",
        "current_wind_speed",
    )

    cloud_cover = _get_numeric(
        snapshot,
        "cloud_cover",
        "cloudcover",
    )

    solar_radiation = _get_numeric(
        snapshot,
        "solar_radiation",
        "shortwave_radiation",
    )

    et0 = _get_numeric(
        snapshot,
        "et0",
        "et0_fao_evapotranspiration",
        "evapotranspiration",
    )

    soil_temperature = _get_numeric(
        snapshot,
        "soil_temperature",
        "soil_temperature_0cm",
        "soil_temp",
    )

    normalized = {
        **snapshot,
        "temperature": temperature,
        "dew_point": dew_point,
        "wind_speed": wind_speed,
        "cloud_cover": cloud_cover,
        "solar_radiation": solar_radiation,
        "et0": et0,
        "soil_temperature": soil_temperature,
    }

    if temperature is not None and dew_point is not None:
        normalized["dewpoint_spread"] = temperature - dew_point
    else:
        normalized["dewpoint_spread"] = None

    return normalized


# ============================================================
# PESTICIDE / SPRAY DETECTION
# ============================================================

SPRAY_KEYWORDS = [
    "fungicide",
    "insecticide",
    "pesticide",
    "spray",
    "copper oxychloride",
    "magnesium sulfate",
    "epsom salt",
    "muriate of potash",
    "kno3",
    "potassium nitrate",
    "nitrogenous fertilizer",
    "nitrogen correction",
    "foliar",
]


def _contains_spray_or_product_reference(
    risk_entry: dict[str, Any],
) -> bool:
    """
    Determine whether an advisory contains a chemical/product,
    spray, foliar application, or dosage-type recommendation.

    This controls whether the global pesticide safety disclaimer
    is attached.
    """

    text_parts = []

    for field in [
        "summary",
        "immediate_actions",
        "prevention",
        "monitoring",
    ]:
        value = risk_entry.get(field)

        if isinstance(value, str):
            text_parts.append(value)

        elif isinstance(value, list):
            text_parts.extend(
                item for item in value
                if isinstance(item, str)
            )

    combined_text = " ".join(text_parts).lower()

    return any(
        keyword in combined_text
        for keyword in SPRAY_KEYWORDS
    )


# ============================================================
# ENVIRONMENTAL MODIFIERS
# ============================================================

def _condition_matches_modifier(
    condition_id: str,
    modifier: dict[str, Any],
) -> bool:
    """
    Determine whether an environmental modifier applies to
    the selected condition.
    """

    applies_to_conditions = modifier.get(
        "applies_to_conditions"
    )

    if applies_to_conditions is not None:
        return condition_id in applies_to_conditions

    applies_to = modifier.get("applies_to")

    if applies_to == "spray_or_fungicide_or_insecticide_advisories":
        return True

    return False


def _evaluate_modifier(
    modifier: dict[str, Any],
    weather: dict[str, Any],
    has_spray_action: bool,
) -> bool:
    """
    Evaluate one machine-readable environmental rule.

    Returns True only when:
        1. required weather data exists
        2. the trigger condition is satisfied
    """

    modifier_id = modifier.get("id")

    # --------------------------------------------------------
    # Spray/wind modifier
    # --------------------------------------------------------

    if modifier_id == "high_wind":
        if not has_spray_action:
            return False

        value = weather.get("wind_speed")

        if value is None:
            return False

        return value > modifier["threshold"]

    # --------------------------------------------------------
    # Dewpoint spread
    # --------------------------------------------------------

    if modifier_id == "narrow_dewpoint_spread":
        value = weather.get("dewpoint_spread")

        if value is None:
            return False

        return value < modifier["threshold"]

    # --------------------------------------------------------
    # Cloud cover
    # --------------------------------------------------------

    if modifier_id == "high_cloud_cover":
        value = weather.get("cloud_cover")

        if value is None:
            return False

        return value >= modifier["threshold"]

    # --------------------------------------------------------
    # Solar radiation
    # --------------------------------------------------------

    if modifier_id == "high_solar_radiation":
        value = weather.get("solar_radiation")

        if value is None:
            return False

        # This modifier requires contextual evidence of
        # significant defoliation. The current API does not
        # yet have a dedicated defoliation field, so we do not
        # trigger it automatically.
        return False

    # --------------------------------------------------------
    # ET0
    # --------------------------------------------------------

    if modifier_id == "high_et0":
        value = weather.get("et0")

        if value is None:
            return False

        return value >= modifier["threshold"]

    # --------------------------------------------------------
    # Soil temperature
    # --------------------------------------------------------

    if modifier_id == "low_soil_temperature":
        value = weather.get("soil_temperature")

        if value is None:
            return False

        return value < modifier["threshold"]

    return False


def _evaluate_environmental_modifiers(
    condition_id: str,
    risk_entry: dict[str, Any],
    weather_snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Evaluate every global environmental modifier.

    Only triggered modifiers are returned.
    """

    weather = _extract_weather_snapshot(
        weather_snapshot
    )

    has_spray_action = _contains_spray_or_product_reference(
        risk_entry
    )

    triggered = []

    for modifier in ADVISORY_DATA["global"].get(
        "environmental_modifiers",
        [],
    ):
        if not _condition_matches_modifier(
            condition_id,
            modifier,
        ):
            continue

        if not _evaluate_modifier(
            modifier,
            weather,
            has_spray_action,
        ):
            continue

        triggered.append(
            {
                "id": modifier.get("id"),
                "parameter": modifier.get("parameter"),
                "trigger": {
                    "operator": modifier.get("operator"),
                    "threshold": modifier.get("threshold"),
                    "unit": modifier.get("unit"),
                },
                "note": modifier.get("note"),
            }
        )

    return triggered


# ============================================================
# MAIN ADVISORY FUNCTION
# ============================================================

def generate_advisory(
    disease: str,
    risk_level: str,
    confidence: float,
    weather_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a deterministic farmer advisory.

    Inputs:
        disease:
            AI model label, e.g. "Late Blight"

        risk_level:
            Risk Engine output:
            LOW / MODERATE / HIGH / CRITICAL

        confidence:
            AI classification confidence, 0.0 - 1.0

        weather_snapshot:
            Weather information already extracted by Risk Engine.

    Important:
        This function does NOT calculate disease risk.
        It does NOT recalculate the Risk Engine score.

        It only:
            1. Looks up the advisory.
            2. Evaluates environmental modifiers.
            3. Adds confidence warning when required.
            4. Adds pesticide safety disclaimer when required.
    """

    # --------------------------------------------------------
    # Validate confidence
    # --------------------------------------------------------

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        raise ValueError("confidence must be numeric.")

    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            "confidence must be between 0.0 and 1.0."
        )

    # --------------------------------------------------------
    # Deterministic lookup
    # --------------------------------------------------------

    condition, risk_entry = _get_advisory_entry(
        disease,
        risk_level,
    )

    normalized_risk_level = _normalize_risk_level(
        risk_level
    )

    # --------------------------------------------------------
    # Environmental modifiers
    # --------------------------------------------------------

    environmental_modifiers = (
        _evaluate_environmental_modifiers(
            condition_id=condition["condition_id"],
            risk_entry=risk_entry,
            weather_snapshot=weather_snapshot,
        )
    )

    # --------------------------------------------------------
    # Low-confidence warning
    # --------------------------------------------------------

    low_confidence_warning = None

    if confidence < LOW_CONFIDENCE_THRESHOLD:
        low_confidence_warning = ADVISORY_DATA[
            "global"
        ]["low_confidence_note"]

    # --------------------------------------------------------
    # Pesticide safety disclaimer
    # --------------------------------------------------------

    pesticide_safety_disclaimer = None

    if _contains_spray_or_product_reference(
        risk_entry
    ):
        pesticide_safety_disclaimer = ADVISORY_DATA[
            "global"
        ]["pesticide_safety_disclaimer"]

    # --------------------------------------------------------
    # Final structured response
    # --------------------------------------------------------

    return {
        "condition_id": condition["condition_id"],
        "model_label": condition["model_label"],
        "category": condition["category"],
        "cause": condition.get("cause"),

        "risk_level": normalized_risk_level,

        "summary": risk_entry["summary"],
        "immediate_actions": risk_entry["immediate_actions"],
        "prevention": risk_entry["prevention"],
        "monitoring": risk_entry["monitoring"],

        "expert_referral": risk_entry[
            "expert_referral"
        ],

        "environmental_modifiers": (
            environmental_modifiers
        ),

        "low_confidence_warning": (
            low_confidence_warning
        ),

        "pesticide_safety_disclaimer": (
            pesticide_safety_disclaimer
        ),

        "sources": {
            "display_source": condition.get(
                "display_source"
            ),
            "source": condition.get(
                "source"
            ),
            "source_reference": condition.get(
                "source_reference",
                [],
            ),
        },

        "engine": {
            "name": "deterministic-advisory-engine",
            "version": "1.0.0",
        },
    }