
from advisory_engine import generate_advisory, ADVISORY_DATA


def test_all_32_combinations():
    count = 0

    for advisory in ADVISORY_DATA["advisories"]:
        disease = advisory["model_label"]

        for risk_level in ["LOW", "MODERATE", "HIGH", "CRITICAL"]:
            result = generate_advisory(
                disease=disease,
                risk_level=risk_level,
                confidence=0.90,
                weather_snapshot={
                    "temperature": 26,
                    "dew_point": 24,
                    "wind_speed": 10,
                    "cloud_cover": 50,
                    "et0": 3,
                    "soil_temperature": 22,
                },
            )

            assert result["model_label"] == disease
            assert result["risk_level"] == risk_level
            assert result["summary"]
            assert isinstance(result["immediate_actions"], list)
            assert isinstance(result["prevention"], list)
            assert isinstance(result["monitoring"], list)
            assert isinstance(result["expert_referral"], bool)
            assert "sources" in result
            assert result["engine"]["name"] == "deterministic-advisory-engine"

            count += 1

    assert count == 32
    print(f"PASS: All {count} advisory combinations work.")


def test_low_confidence_warning():
    result = generate_advisory(
        "Late Blight",
        "HIGH",
        0.69,
    )

    assert result["low_confidence_warning"] is not None
    print("PASS: Low-confidence warning works.")


def test_70_percent_confidence():
    result = generate_advisory(
        "Late Blight",
        "HIGH",
        0.70,
    )

    assert result["low_confidence_warning"] is None
    print("PASS: 70% confidence threshold works.")


def test_high_wind_modifier():
    result = generate_advisory(
        "Late Blight",
        "HIGH",
        0.90,
        {
            "temperature": 26,
            "dew_point": 25,
            "wind_speed": 20,
            "cloud_cover": 50,
        },
    )

    modifier_ids = [
        modifier["id"]
        for modifier in result["environmental_modifiers"]
    ]

    assert "high_wind" in modifier_ids
    print("PASS: High-wind modifier works.")


def test_dewpoint_modifier():
    result = generate_advisory(
        "Late Blight",
        "HIGH",
        0.90,
        {
            "temperature": 26,
            "dew_point": 25.5,
            "wind_speed": 10,
            "cloud_cover": 50,
        },
    )

    modifier_ids = [
        modifier["id"]
        for modifier in result["environmental_modifiers"]
    ]

    assert "narrow_dewpoint_spread" in modifier_ids
    print("PASS: Dewpoint modifier works.")


def test_cloud_cover_modifier():
    result = generate_advisory(
        "Late Blight",
        "HIGH",
        0.90,
        {
            "temperature": 26,
            "dew_point": 20,
            "wind_speed": 10,
            "cloud_cover": 90,
        },
    )

    modifier_ids = [
        modifier["id"]
        for modifier in result["environmental_modifiers"]
    ]

    assert "high_cloud_cover" in modifier_ids
    print("PASS: Cloud-cover modifier works.")


def test_invalid_disease():
    try:
        generate_advisory("Fake Disease", "HIGH", 0.90)
        assert False
    except ValueError:
        print("PASS: Invalid disease rejected.")


def test_invalid_risk_level():
    try:
        generate_advisory("Late Blight", "EXTREME", 0.90)
        assert False
    except ValueError:
        print("PASS: Invalid risk level rejected.")


if __name__ == "__main__":
    test_all_32_combinations()
    test_low_confidence_warning()
    test_70_percent_confidence()
    test_high_wind_modifier()
    test_dewpoint_modifier()
    test_cloud_cover_modifier()
    test_invalid_disease()
    test_invalid_risk_level()

    print("\nALL ADVISORY TESTS PASSED.")