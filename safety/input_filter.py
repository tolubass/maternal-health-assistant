"""
Input filter — Layer 2 of the safety stack.

Catches requests that the assistant must never attempt to answer:
- Diagnosis requests ("do I have X", "is this cancer")
- Prescription requests ("what dose of X", "prescribe me")
- Clearly off-topic content

Returns a tuple: (is_blocked: bool, reason: str)
"""
import re
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Diagnosis request patterns
# -------------------------------------------------------
DIAGNOSIS_PATTERNS = [
    r"\bdo\s+i\s+have\b",
    r"\bdo\s+i\s+(have|suffer\s+from)\b",
    r"\bis\s+(this|it)\s+(cancer|a\s+disease|an?\s+infection|hiv|aids|malaria)\b",
    r"\bwhat\s+(disease|condition|illness)\s+do\s+i\s+have\b",
    r"\bdiagnose\s+me\b",
    r"\bwhat'?s\s+wrong\s+with\s+me\b",
    r"\bam\s+i\s+(sick|pregnant|infected|positive)\b",
    r"\btest\s+results?\s+(mean|say|show)\b",
]

# -------------------------------------------------------
# Prescription request patterns
# -------------------------------------------------------
PRESCRIPTION_PATTERNS = [
    r"\bprescribe\s+(me|her|him|us)\b",
    r"\bwhat\s+(dose|dosage|mg|milligram)\b",
    r"\bhow\s+much\s+(of\s+)?(drug|medication|medicine|tablet|pill)\b",
    r"\bwhich\s+(drug|medication|medicine|antibiotic)\s+(should|can|to)\s+(i|she|he|we)\s+take\b",
    r"\bcan\s+i\s+take\s+\w+\s+(during|while|when)\s+pregnan(t|cy)\b",
    r"\bis\s+\w+\s+safe\s+(during|in|for)\s+pregnan(t|cy)\b",
    r"\btake\s+\d+\s*(mg|ml|tablets?|pills?)\b",
]

# -------------------------------------------------------
# Clearly off-topic patterns
# -------------------------------------------------------
OFFTOPIC_PATTERNS = [
    r"\b(bitcoin|crypto|forex|stock\s+market|invest(ment|ing)?)\b",
    r"\b(football|soccer|sport(s)?|nfl|nba|premier\s+league)\b",
    r"\b(recipe|cook(ing)?|food\s+preparation)\b",
    r"\b(politics|election|president|governor|senator)\b",
    r"\b(movie|film|series|netflix|music|song|lyrics)\b",
    r"\b(hack(ing)?|password|credit\s+card|bank\s+account)\b",
]

_DIAGNOSIS  = [re.compile(p, re.IGNORECASE) for p in DIAGNOSIS_PATTERNS]
_PRESCRIPTION = [re.compile(p, re.IGNORECASE) for p in PRESCRIPTION_PATTERNS]
_OFFTOPIC   = [re.compile(p, re.IGNORECASE) for p in OFFTOPIC_PATTERNS]


def check_input(text: str) -> tuple[bool, str]:
    """
    Returns (True, reason) if the input should be blocked.
    Returns (False, "") if the input is acceptable.
    """
    for pattern in _DIAGNOSIS:
        if pattern.search(text):
            logger.info(f"Input blocked — diagnosis request: '{text[:80]}'")
            return True, "diagnosis"

    for pattern in _PRESCRIPTION:
        if pattern.search(text):
            logger.info(f"Input blocked — prescription request: '{text[:80]}'")
            return True, "prescription"

    for pattern in _OFFTOPIC:
        if pattern.search(text):
            logger.info(f"Input blocked — off-topic: '{text[:80]}'")
            return True, "offtopic"

    return False, ""


BLOCK_MESSAGES = {
    "diagnosis": (
        "I'm not able to diagnose medical conditions. "
        "Please visit a qualified health worker or clinic for a proper assessment. "
        "I can share general health information to help you understand symptoms, "
        "but only a healthcare provider can give you a diagnosis."
    ),
    "prescription": (
        "I'm not able to prescribe medications or recommend dosages. "
        "Please consult a qualified health worker or pharmacist. "
        "Taking the wrong medication or dose during pregnancy can be harmful."
    ),
    "offtopic": (
        "I can only help with maternal and child health topics — "
        "pregnancy, antenatal care, childbirth, newborn care, nutrition, and related subjects. "
        "Please ask a health-related question and I'll do my best to help."
    ),
}