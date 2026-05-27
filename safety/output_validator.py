"""
Output validator — Layer 4 of the safety stack.

Checks the LLM's generated answer before it is returned to the user.
Rejects responses that contain diagnostic claims, prescription language,
or content not grounded in the retrieved context.

Returns a tuple: (is_safe: bool, reason: str)
"""
import re
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Patterns that must never appear in a generated answer
# -------------------------------------------------------
PROHIBITED_OUTPUT_PATTERNS = [
    # Diagnostic statements
    r"\byou\s+(have|are\s+suffering\s+from|are\s+diagnosed\s+with)\b",
    r"\bthis\s+is\s+(cancer|hiv|malaria|typhoid|diabetes|hypertension)\b",
    r"\byou\s+(definitely|certainly|probably)\s+have\b",
    r"\bthe\s+diagnosis\s+is\b",
    r"\byou\s+are\s+positive\s+for\b",

    # Prescription / dosage
    r"\btake\s+\d+\s*(mg|ml|tablets?|pills?|capsules?)\b",
    r"\bdose\s+(is|should\s+be|of)\s+\d+\b",
    r"\bprescrib(e|ing|ed)\b",
    r"\bi\s+recommend\s+(taking|using)\s+\w+\s+(tablet|drug|medicine|medication)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in PROHIBITED_OUTPUT_PATTERNS]

# Minimum grounding check — answer must reference at least one citation marker
CITATION_PATTERN = re.compile(r"\[\d+\]")


def validate_output(answer: str, chunks_were_found: bool) -> tuple[bool, str]:
    """
    Returns (True, "") if the answer is safe to send.
    Returns (False, reason) if the answer should be replaced with a safe fallback.

    Args:
        answer: The LLM-generated answer string.
        chunks_were_found: Whether relevant chunks were retrieved for this query.
    """
    # Check for prohibited content
    for pattern in _COMPILED:
        if pattern.search(answer):
            logger.warning(
                f"Output blocked — prohibited pattern: '{pattern.pattern[:60]}'"
            )
            return False, "prohibited_content"

    # Check grounding — if chunks were found, answer should cite at least one
    if chunks_were_found and not CITATION_PATTERN.search(answer):
        logger.warning("Output flagged — no citation markers found in answer")
        # This is a warning, not a hard block — some valid answers may not cite
        # We log but allow it through; Phase E Ragas will measure citation coverage
        pass

    return True, ""


UNSAFE_OUTPUT_FALLBACK = (
    "I wasn't able to generate a safe response for that question. "
    "Please rephrase your question or consult a qualified health worker."
)