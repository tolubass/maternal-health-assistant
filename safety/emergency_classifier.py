"""
Emergency classifier — Layer 1 of the safety stack.

Detects life-threatening symptoms in user input BEFORE retrieval runs.
On a positive match, the request is short-circuited and a pre-configured
emergency response is returned immediately. The LLM is never called.

Design principle: it is always safer to over-trigger than to miss a real emergency.
"""
import re
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Emergency keyword groups
# Each group targets a distinct clinical danger sign.
# -------------------------------------------------------
EMERGENCY_PATTERNS = [
    # Haemorrhage / bleeding
    r"\bheavy\s+bleed(ing)?\b",
    r"\bbleed(ing)?\s+heavily\b",
    r"\bbleed(ing)?\s+a\s+lot\b",
    r"\bblood\s+everywhere\b",
    r"\bpostpartum\s+hemo?rrhage\b",
    r"\bpph\b",
    r"\bbleed(ing)?\s+won'?t\s+stop\b",
    r"\bsoak(ing|ed)\s+(through\s+)?(pad|cloth|wrapper)s?\b",
    r"\bsoak(ing|ed)\s+more\s+than\s+one\s+(pad|cloth)\b",

    # Convulsions / seizures
    r"\bconvuls(ion|ing|ed)s?\b",
    r"\bseizure?s?\b",
    r"\bfit(s|ting)?\b",
    r"\bshak(ing|e)\s+(uncontrollably|violently)\b",
    r"\beclampsia\b",
    r"\bpre-?eclampsia\b",

    # Loss of consciousness
    r"\blos(t|s(ing)?)\s+consciousness\b",
    r"\bunconscious\b",
    r"\bpassed?\s+out\b",
    r"\bfaint(ed|ing)?\b",
    r"\bnot\s+(waking\s+up|responding|breathing)\b",
    r"\bcan'?t\s+wake\s+(her|him|them|baby|up)\b",

    # Severe abdominal pain
    r"\bsevere\s+(abdominal|stomach|belly|lower)\s+pain\b",
    r"\bextreme\s+(abdominal|stomach|belly)\s+pain\b",
    r"\bagoniz(ing|ed)\s+pain\b",
    r"\bsudden\s+severe\s+pain\b",
    r"\bcan'?t\s+(bear|stand|take)\s+the\s+pain\b",

    # Absent fetal movement
    r"\bno\s+(fetal|foetal|baby)\s+movement\b",
    r"\bbaby\s+(not|isn'?t|hasn'?t)\s+(moving|kicked?|kicked?\s+today)\b",
    r"\bbaby\s+has\s+not\s+been\s+moving\b",
    r"\bbaby\s+hasn'?t\s+been\s+moving\b",
    r"\bnot\s+(moving|kicked?)\s+(since|for|today|all\s+day)\b",
    r"\bstopped?\s+feel(ing)?\s+(baby|fetal|foetal)\s+movement\b",
    r"\bhaven'?t\s+felt\s+(baby|movement|kicks?)\b",
    r"\bno\s+kick(s|ing)?\b",

    # Newborn fever / danger signs
    r"\bnewborn\s+(fever|temperature)\b",
    r"\bnewborn\s+has\s+(a\s+)?(high\s+)?fever\b",
    r"\bbaby\s+(has\s+)?(high\s+)?fever\b",
    r"\bbaby\s+has\s+(a\s+)?(high\s+)?fever\b",
    r"\binfant\s+has\s+(a\s+)?(high\s+)?fever\b",
    r"\binfant\s+(fever|temperature|not\s+feeding)\b",
    r"\bbaby\s+not\s+(breathing|feeding|responding|waking)\b",
    r"\bnewborn\s+not\s+(breathing|feeding|waking|responding)\b",
    r"\byellow\s+(skin|baby|newborn|eyes)\b",
    r"\bjaundice\b",

    # Severe breathing difficulty
    r"\bcan'?t\s+breath(e|ing)?\b",
    r"\bbreath(ing)?\s+(difficulty|problem|trouble)\b",
    r"\bshortness?\s+of\s+breath\b",
    r"\bgasping\b",
    r"\bchok(ing|ed)\b",

    # Severe headache / vision (eclampsia warning signs)
    r"\bsevere\s+headache\b",
    r"\bblurred?\s+vision\b",
    r"\bblind(ness|ing)?\s+(suddenly|sudden)\b",
    r"\bsees?\s+spots?\b",
    r"\bsudden\s+(vision|sight)\s+(loss|change|problem)\b",

    # Prolapsed cord / placenta
    r"\bcord\s+(prolapse|coming\s+out|hanging)\b",
    r"\bplacenta\s+(previa|abruption)\b",

    # Sepsis / infection signs
    r"\bhigh\s+fever\s+(in\s+)?pregnan(t|cy)\b",
    r"\bfever\s+(above|over|more\s+than)\s+3[89]\b",
    r"\bsmell(s|y|ing)?\s+(bad|foul|horrible)\s+(discharge|fluid|bleed)\b",
    r"\bfoul[\s-]smell(ing)?\s+(discharge|fluid|lochia)\b",
]

# Compile once at import time for performance
_COMPILED = [re.compile(p, re.IGNORECASE) for p in EMERGENCY_PATTERNS]

# Pidgin / informal variants as plain substring matches
EMERGENCY_SUBSTRINGS = [
    "i dey bleed", "she dey bleed", "blood plenty",
    "baby no dey move", "pikin no dey breathe",
    "no dey breathe", "she faint", "she don faint",
    "she don collapse", "collapse", "she unconscious",
    "baby yellow", "pikin yellow", "convulsion",
]


def is_emergency(text: str) -> bool:
    """
    Return True if the text contains any emergency trigger.
    Checks compiled regex patterns first, then plain substring matches.
    """
    text_lower = text.lower()

    for pattern in _COMPILED:
        if pattern.search(text):
            logger.warning(f"Emergency trigger matched: pattern='{pattern.pattern[:50]}'")
            return True

    for phrase in EMERGENCY_SUBSTRINGS:
        if phrase in text_lower:
            logger.warning(f"Emergency trigger matched: substring='{phrase}'")
            return True

    return False