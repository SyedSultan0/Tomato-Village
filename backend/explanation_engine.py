# ============================================================
# EXPLANATION ENGINE — M4.4
# ============================================================
#
# Optional natural-language layer over the deterministic pipeline.
#
# This module does NOT:
#   - diagnose a condition
#   - compute risk
#   - decide escalation
#   - invent treatments
#   - retrieve knowledge
#
# It receives the already-determined facts and produces a
# farmer-friendly paragraph. If Gemini is unavailable, it
# falls back to a deterministic template so the API response
# is always complete.
#
# Provider: Google Gemini (free tier).
# Env var:  GEMINI_API_KEY
# Toggle:   ENABLE_LLM_EXPLANATION (default "true")
# ============================================================

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ENABLE_LLM = os.getenv(
    "ENABLE_LLM_EXPLANATION", "true"
).strip().lower() in ("1", "true", "yes", "on")

GEMINI_MODEL = "gemini-3.6-flash"

# Lazy-import the SDK only if we actually need it, so the
# rest of the pipeline works even if google-genai is missing.
_genai_client = None


def _get_genai_client():
    global _genai_client

    if _genai_client is not None:
        return _genai_client

    if not GEMINI_API_KEY:
        return None

    try:
        from google import genai  # type: ignore

        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
        return _genai_client

    except Exception as e:
        print("Gemini client init failed:", str(e))
        return None


# ============================================================
# TEMPLATE FALLBACK (deterministic)
# ============================================================

def _template_explanation(
    prediction: dict,
    risk: dict,
    advisory: dict,
    escalation: dict,
    evidence: list[dict] | None,
) -> str:
    """
    Deterministic explanation built from the structured pipeline
    output. Always works. Never calls out to any external service.
    """

    parts = []

    pred_class = prediction.get("predicted_class") or "Unknown"
    confidence = prediction.get("confidence")

    if confidence is not None:
        parts.append(
            f"AI classification: {pred_class} "
            f"(confidence {confidence * 100:.1f}%)."
        )
    else:
        parts.append(f"AI classification: {pred_class}.")

    risk_level = risk.get("risk_level")
    risk_score = risk.get("risk_score")

    if risk_level is not None and risk_score is not None:
        parts.append(
            f"Environmental risk for this condition is currently "
            f"{risk_level} ({risk_score}/100)."
        )
    elif risk_level is not None:
        parts.append(
            f"Environmental risk is currently {risk_level}."
        )

    summary = advisory.get("summary")
    if summary:
        parts.append(summary)

    actions = advisory.get("immediate_actions") or []
    if actions:
        parts.append(
            "Immediate actions: " + "; ".join(actions) + "."
        )

    decision = escalation.get("decision")
    if decision == "EXPERT_REVIEW":
        parts.append(
            "We recommend contacting your local KVK or "
            "agriculture extension officer."
        )
    elif decision == "ATTENTION":
        parts.append(
            "This case is flagged for attention — follow the "
            "advisory above and monitor the crop."
        )

    if evidence:
        src = evidence[0].get("display_source")
        if src:
            parts.append(f"Source: {src}.")

    return " ".join(parts)


# ============================================================
# LLM PROMPT
# ============================================================

_SYSTEM_INSTRUCTION = (
    "You write short crop-health messages for farmers. "
    "The facts are already decided by a farming system. "
    "You only put them into very simple English.\n\n"

    "OUTPUT FORMAT:\n"
    "Write exactly 5 short sentences, in this order:\n"
    "  1. What the system found on the plant.\n"
    "  2. Whether the weather makes the problem worse.\n"
    "  3. What the farmer should do this week.\n"
    "  4. What else the farmer should check while doing it.\n"
    "  5. When to check the plant again, and the source.\n\n"

    "WRITING RULES:\n"
    "- One idea per sentence. Short sentences only.\n"
    "- Use very simple words. No jargon. No big words.\n"
    "- Do not use words like: 'underlying', 'imbalance', "
    "'potentially', 'provisional', 'nonetheless', 'AI', "
    "'algorithm', 'environmental favorability'.\n"
    "- Say 'the system found' or 'the system detected'. "
    "Never say 'the plant has' as a confirmed fact.\n"
    "- Do not invent any product, spray, dose, or number "
    "that is not already in the facts.\n"
    "- Do not change the risk level.\n\n"

    "Write only in English. Do not skip any of the 5 sentences."
)


def _build_prompt(
    prediction: dict,
    risk: dict,
    advisory: dict,
    escalation: dict,
    evidence: list[dict] | None,
) -> str:
    """
    Build a compact prompt. We send only the fields the LLM needs
    to explain — nothing more, nothing less.
    """

    import json

    payload = {
        "prediction": {
            "predicted_class": prediction.get("predicted_class"),
            "confidence": prediction.get("confidence"),
        },
        "risk": {
            "risk_level": risk.get("risk_level"),
            "risk_score": risk.get("risk_score"),
        },
        "advisory": {
            "summary": advisory.get("summary"),
            "immediate_actions": advisory.get("immediate_actions") or [],
            "prevention": advisory.get("prevention") or [],
            "monitoring": advisory.get("monitoring") or [],
        },
        "escalation": {
            "decision": escalation.get("decision"),
            "reasons": escalation.get("reasons") or [],
        },
        "evidence_source": (
            evidence[0].get("display_source")
            if evidence
            else None
        ),
    }

    return (
        "Facts determined by the deterministic pipeline:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\nWrite the farmer-facing explanation now."
    )


# ============================================================
# PUBLIC API
# ============================================================

def generate_explanation(
    prediction: dict,
    risk: dict,
    advisory: dict,
    escalation: dict,
    evidence: list[dict] | None = None,
) -> dict:
    """
    Produce a farmer-friendly explanation.

    Always returns the same shape:

        {
            "available": bool,
            "provider": "gemini" | "template" | None,
            "model": str | None,
            "text": str | None,
            "error": str | None,
        }

    The pipeline never depends on this function succeeding.
    If anything fails, the template fallback is returned with
    provider="template" so the response is still complete.
    """

    # --------------------------------------------------------
    # Short-circuit: prediction and risk are the minimum
    # necessary inputs. Without them, there is nothing to
    # explain.
    # --------------------------------------------------------

    if not prediction or not risk:
        return {
            "available": False,
            "provider": None,
            "model": None,
            "text": None,
            "error": "Missing prediction or risk.",
        }

    # --------------------------------------------------------
    # If LLM is disabled or unconfigured, go straight to
    # the template.
    # --------------------------------------------------------

    if not ENABLE_LLM or not GEMINI_API_KEY:
        return {
            "available": True,
            "provider": "template",
            "model": "deterministic-template-v1",
            "text": _template_explanation(
                prediction, risk, advisory, escalation, evidence
            ),
            "error": None,
        }

    # --------------------------------------------------------
    # Attempt Gemini.
    # --------------------------------------------------------

    client = _get_genai_client()

    if client is None:
        return {
            "available": True,
            "provider": "template",
            "model": "deterministic-template-v1",
            "text": _template_explanation(
                prediction, risk, advisory, escalation, evidence
            ),
            "error": "Gemini client unavailable.",
        }

    try:
        from google.genai import types  # type: ignore

        prompt = _build_prompt(
            prediction, risk, advisory, escalation, evidence
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                temperature=0.3,
                max_output_tokens=600,
            ),
        )

        text = getattr(response, "text", None)

        if not text:
            raise RuntimeError("Gemini returned an empty response.")

        return {
            "available": True,
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "text": text.strip(),
            "error": None,
        }

    except Exception as e:

        print("Gemini call failed:", str(e))

        return {
            "available": True,
            "provider": "template",
            "model": "deterministic-template-v1",
            "text": _template_explanation(
                prediction, risk, advisory, escalation, evidence
            ),
            "error": str(e),
        }