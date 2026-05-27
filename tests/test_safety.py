"""
Tests for the safety layer.
Run: pytest tests/test_safety.py -v
"""
import pytest
from safety.emergency_classifier import is_emergency
from safety.input_filter import check_input, BLOCK_MESSAGES
from safety.output_validator import validate_output


# -------------------------------------------------------
# Emergency classifier
# -------------------------------------------------------
class TestEmergencyClassifier:

    def test_heavy_bleeding_triggers(self):
        assert is_emergency("she is having heavy bleeding") is True

    def test_convulsion_triggers(self):
        assert is_emergency("my wife is having convulsions") is True

    def test_no_fetal_movement_triggers(self):
        assert is_emergency("baby has not been moving since yesterday") is True

    def test_unconscious_triggers(self):
        assert is_emergency("she passed out and is unconscious") is True

    def test_newborn_fever_triggers(self):
        assert is_emergency("my newborn has a high fever") is True

    def test_cant_breathe_triggers(self):
        assert is_emergency("she can't breathe properly") is True

    def test_severe_headache_triggers(self):
        assert is_emergency("I have a severe headache and blurred vision") is True

    def test_pidgin_bleeding_triggers(self):
        assert is_emergency("i dey bleed plenty") is True

    def test_pidgin_collapse_triggers(self):
        assert is_emergency("she don collapse") is True

    def test_normal_question_not_emergency(self):
        assert is_emergency("what should I eat during pregnancy?") is False

    def test_greeting_not_emergency(self):
        assert is_emergency("hello how are you") is False

    def test_general_pain_not_emergency(self):
        # "back pain" alone should not trigger — not a listed danger sign
        assert is_emergency("I have some back pain") is False

    def test_case_insensitive(self):
        assert is_emergency("HEAVY BLEEDING") is True
        assert is_emergency("Convulsions") is True


# -------------------------------------------------------
# Input filter
# -------------------------------------------------------
class TestInputFilter:

    def test_diagnosis_request_blocked(self):
        blocked, reason = check_input("do I have malaria?")
        assert blocked is True
        assert reason == "diagnosis"

    def test_prescription_request_blocked(self):
        blocked, reason = check_input("what dose of paracetamol should I take?")
        assert blocked is True
        assert reason == "prescription"

    def test_offtopic_blocked(self):
        blocked, reason = check_input("what is the bitcoin price today?")
        assert blocked is True
        assert reason == "offtopic"

    def test_valid_health_question_allowed(self):
        blocked, reason = check_input("what are the danger signs in pregnancy?")
        assert blocked is False
        assert reason == ""

    def test_antenatal_question_allowed(self):
        blocked, reason = check_input("how many antenatal visits should I have?")
        assert blocked is False

    def test_nutrition_question_allowed(self):
        blocked, reason = check_input("what should a pregnant woman eat?")
        assert blocked is False

    def test_block_messages_exist_for_all_reasons(self):
        for reason in ("diagnosis", "prescription", "offtopic"):
            assert reason in BLOCK_MESSAGES
            assert len(BLOCK_MESSAGES[reason]) > 0


# -------------------------------------------------------
# Output validator
# -------------------------------------------------------
class TestOutputValidator:

    def test_clean_answer_passes(self):
        answer = "Antenatal care involves regular checkups [1]. It helps monitor the baby's health [2]."
        safe, reason = validate_output(answer, chunks_were_found=True)
        assert safe is True
        assert reason == ""

    def test_diagnostic_claim_blocked(self):
        answer = "Based on your symptoms, you have malaria and should seek treatment."
        safe, reason = validate_output(answer, chunks_were_found=True)
        assert safe is False
        assert reason == "prohibited_content"

    def test_prescription_in_answer_blocked(self):
        answer = "You should take 500mg of amoxicillin three times daily."
        safe, reason = validate_output(answer, chunks_were_found=True)
        assert safe is False
        assert reason == "prohibited_content"

    def test_answer_without_chunks_passes_if_clean(self):
        answer = "I don't have information about that. Please consult a health worker."
        safe, reason = validate_output(answer, chunks_were_found=False)
        assert safe is True

    def test_case_insensitive_detection(self):
        answer = "YOU HAVE DIABETES based on your symptoms."
        safe, reason = validate_output(answer, chunks_were_found=True)
        assert safe is False