"""
Pre-configured emergency responses.
These are returned immediately when an emergency is detected.
The LLM is never called for emergencies — responses are deterministic,
fast, and cannot hallucinate.
"""

EMERGENCY_RESPONSE = """🚨 **This sounds like a medical emergency. Please seek immediate care.**

**Go to the nearest health facility RIGHT NOW** or call emergency services.

---

**While you wait or travel:**
- Stay calm and keep the person still and comfortable
- Do not give food, water, or any medication without medical advice
- If she is unconscious, lay her on her left side
- If a newborn is not breathing, do not shake — seek help immediately

---

**Emergency contacts in Nigeria:**
- **National Emergency:** 112
- **NEMA Emergency Line:** 0800-CALLNEMA (0800-2255-6362)
- **Lagos State Emergency:** 767 or 112
- **Abuja FCTA Emergency:** 112

---

⚠️ **This assistant cannot replace emergency medical care.**
Please do not delay seeking help while waiting for a response here.
"""

EMERGENCY_KEYWORDS_RESPONSE = EMERGENCY_RESPONSE  # alias for clarity