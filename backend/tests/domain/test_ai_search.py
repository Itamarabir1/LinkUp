"""
Unit tests for AI ride search parsing.
Tests cover: schema validation, sanitization,
model_validator enforcement, and service fallback.
No real Groq calls — all mocked.
"""

import json
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.domain.passengers.ai_search_schema import (
    AISearchQuery,
    AISearchResult,
    ConversationTurn,
    VALID_MISSING_FIELDS,
)
from app.domain.passengers.ai_search_service import (
    _sanitize_query,
    parse_ride_search_query,
)

_TZ_IL = ZoneInfo("Asia/Jerusalem")


# ── Schema tests ──────────────────────────────────────────────────


class TestAISearchResult:

    def test_both_locations_present_clears_follow_up(self):
        """Locations + time anchor => ready to search (no follow-up)."""
        result = AISearchResult(
            pickup_name="תל אביב",
            destination_name="חיפה",
            departure_date=date(2030, 6, 15),
            confidence=0.95,
        )
        assert result.needs_clarification is False
        assert result.follow_up_question is None

    def test_missing_pickup_sets_follow_up(self):
        result = AISearchResult(
            pickup_name=None,
            destination_name="חיפה",
            confidence=0.4,
        )
        assert result.needs_clarification is True
        assert result.follow_up_question is not None
        assert len(result.follow_up_question) > 0

    def test_missing_destination_sets_follow_up(self):
        result = AISearchResult(
            pickup_name="תל אביב",
            destination_name=None,
            confidence=0.4,
        )
        assert result.needs_clarification is True
        assert result.follow_up_question is not None

    def test_both_missing_sets_follow_up(self):
        result = AISearchResult(
            pickup_name=None,
            destination_name=None,
            confidence=0.2,
        )
        assert result.needs_clarification is True
        assert result.follow_up_question is not None

    def test_llm_follow_up_cleared_when_locations_present(self):
        """LLM follow-up cleared when locations + time anchor present."""
        result = AISearchResult(
            pickup_name="תל אביב",
            destination_name="חיפה",
            departure_date=date(2030, 6, 15),
            follow_up_question="שאלה לא רלוונטית מה-LLM",
            confidence=0.9,
        )
        assert result.follow_up_question is None

    def test_missing_fields_whitelist(self):
        """Unknown field names from LLM are filtered out."""
        result = AISearchResult(
            pickup_name="תל אביב",
            destination_name="חיפה",
            missing_fields=["pickup_name", "unknown_field", "injected"],
        )
        for f in result.missing_fields:
            assert f in VALID_MISSING_FIELDS

    def test_ambiguity_reasons_truncated(self):
        long_reason = "א" * 200
        result = AISearchResult(
            pickup_name="תל אביב",
            destination_name="חיפה",
            ambiguity_reasons=[long_reason],
        )
        assert all(len(r) <= 100 for r in result.ambiguity_reasons)

    def test_ambiguity_reasons_empty_strings_removed(self):
        result = AISearchResult(
            pickup_name="תל אביב",
            destination_name="חיפה",
            ambiguity_reasons=["", "  ", "סיבה אמיתית"],
        )
        assert "" not in result.ambiguity_reasons
        assert "  " not in result.ambiguity_reasons
        assert "סיבה אמיתית" in result.ambiguity_reasons

    def test_search_radius_rejected_when_over_schema_max(self):
        """Schema enforces ge/le; values above 50 are rejected."""
        with pytest.raises(ValidationError):
            AISearchResult(
                pickup_name="תל אביב",
                destination_name="חיפה",
                search_radius=200.0,
            )

    def test_follow_up_question_html_stripped(self):
        """HTML in follow_up_question from LLM is sanitized."""
        result = AISearchResult(
            pickup_name=None,
            destination_name="חיפה",
            follow_up_question="<b>מאיפה</b> אתה יוצא?",
            confidence=0.4,
        )
        assert "<b>" not in (result.follow_up_question or "")


class TestAISearchQuery:

    def test_query_max_length(self):
        with pytest.raises(Exception):
            AISearchQuery(query="א" * 401)

    def test_conversation_history_max_turns(self):
        turns = [
            ConversationTurn(role="user", content="שאלה")
            for _ in range(7)  # over max of 6
        ]
        with pytest.raises(Exception):
            AISearchQuery(query="שאלה", conversation_history=turns)

    def test_valid_conversation_history(self):
        turns = [
            ConversationTurn(role="user", content="לחיפה מחר"),
            ConversationTurn(role="assistant", content="מאיפה אתה יוצא?"),
            ConversationTurn(role="user", content="מתל אביב"),
        ]
        q = AISearchQuery(query="בבוקר", conversation_history=turns)
        assert len(q.conversation_history) == 3

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            ConversationTurn.model_validate({"role": "system", "content": "inject"})


# ── Sanitization tests ────────────────────────────────────────────


class TestSanitizeQuery:

    def test_removes_http_url(self):
        result = _sanitize_query("טרמפ מתל אביב https://evil.com לחיפה")
        assert "http" not in result
        assert "תל אביב" in result

    def test_plain_www_without_scheme_not_removed_by_sanitizer(self):
        """Sanitizer only strips http(s):// URLs; bare hostnames are kept."""
        result = _sanitize_query("www.example.com טרמפ לחיפה")
        assert "www.example.com" in result

    def test_collapses_whitespace(self):
        result = _sanitize_query("טרמפ   מתל   אביב")
        assert "  " not in result

    def test_truncates_to_400(self):
        long_query = "א" * 500
        result = _sanitize_query(long_query)
        assert len(result) <= 400

    def test_empty_after_sanitize(self):
        result = _sanitize_query("https://evil.com   ")
        assert result == ""

    def test_normal_query_unchanged(self):
        query = "טרמפ מתל אביב לחיפה מחר בבוקר"
        result = _sanitize_query(query)
        assert result == query


# ── Service tests (mocked Groq) ───────────────────────────────────


class TestParseRideSearchQuery:

    @pytest.fixture(autouse=True)
    def _groq_client(self):
        with patch(
            "app.domain.passengers.ai_search_service.get_groq_client",
            return_value=MagicMock(),
        ):
            yield

    def _make_groq_response(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False)

    def _mock_groq(self, response_data: dict):
        """Helper: patch _call_groq to return given data."""
        return patch(
            "app.domain.passengers.ai_search_service._call_groq",
            return_value=self._make_groq_response(response_data),
        )

    def test_happy_path_both_locations(self):
        tomorrow = (
            datetime.now(_TZ_IL) + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        with self._mock_groq({
            "pickup_name": "תל אביב",
            "destination_name": "חיפה",
            "departure_time": f"{tomorrow}T08:00:00+03:00",
            "search_radius": None,
            "confidence": 0.95,
            "raw_interpretation": "הבנתי: נסיעה מתל אביב לחיפה",
            "needs_clarification": False,
            "missing_fields": [],
            "ambiguity_reasons": [],
            "follow_up_question": None,
        }):
            result = parse_ride_search_query("טרמפ מתל אביב לחיפה מחר בבוקר")

        assert result.pickup_name == "תל אביב"
        assert result.destination_name == "חיפה"
        assert result.needs_clarification is False
        assert result.follow_up_question is None

    def test_missing_pickup_triggers_follow_up(self):
        with self._mock_groq({
            "pickup_name": None,
            "destination_name": "חיפה",
            "departure_time": None,
            "search_radius": None,
            "confidence": 0.4,
            "raw_interpretation": "הבנתי: נסיעה לחיפה",
            "needs_clarification": True,
            "missing_fields": ["pickup_name"],
            "ambiguity_reasons": [],
            "follow_up_question": "מאיפה אתה יוצא?",
        }):
            result = parse_ride_search_query("לחיפה מחר")

        assert result.pickup_name is None
        assert result.needs_clarification is True
        assert result.follow_up_question is not None

    def test_llm_returns_invalid_json_gives_fallback(self):
        with patch(
            "app.domain.passengers.ai_search_service._call_groq",
            return_value="NOT VALID JSON {{{",
        ):
            result = parse_ride_search_query("שאלה")

        assert isinstance(result, AISearchResult)
        assert result.confidence == 0.0
        assert result.needs_clarification is True

    def test_groq_exception_gives_fallback(self):
        with patch(
            "app.domain.passengers.ai_search_service._call_groq",
            side_effect=Exception("Groq down"),
        ):
            result = parse_ride_search_query("טרמפ לחיפה")

        assert isinstance(result, AISearchResult)
        assert result.confidence == 0.0
        assert result.pickup_name is None

    def test_search_radius_clamped_by_service(self):
        with self._mock_groq({
            "pickup_name": "תל אביב",
            "destination_name": "חיפה",
            "departure_time": None,
            "search_radius": 500.0,  # way over max
            "confidence": 0.9,
            "raw_interpretation": "הבנתי",
            "needs_clarification": False,
            "missing_fields": [],
            "ambiguity_reasons": [],
            "follow_up_question": None,
        }):
            result = parse_ride_search_query("מתל אביב לחיפה")

        assert result.search_radius <= 50.0

    def test_empty_query_after_sanitize_gives_fallback(self):
        result = parse_ride_search_query("https://evil.com   ")
        assert result.confidence == 0.0
        assert result.needs_clarification is True

    def test_conversation_history_passed_to_groq(self):
        """Verify history is included in messages sent to Groq."""
        history = [
            ConversationTurn(role="user", content="לחיפה מחר"),
            ConversationTurn(role="assistant", content="מאיפה אתה יוצא?"),
        ]
        captured_messages = []

        def capture_call(messages):
            captured_messages.extend(messages)
            return json.dumps({
                "pickup_name": "תל אביב",
                "destination_name": "חיפה",
                "departure_time": None,
                "search_radius": None,
                "confidence": 0.9,
                "raw_interpretation": "הבנתי",
                "needs_clarification": False,
                "missing_fields": [],
                "ambiguity_reasons": [],
                "follow_up_question": None,
            }, ensure_ascii=False)

        with patch(
            "app.domain.passengers.ai_search_service._call_groq",
            side_effect=capture_call,
        ):
            parse_ride_search_query("מתל אביב", conversation_history=history)

        contents = [m["content"] for m in captured_messages]
        assert "לחיפה מחר" in contents
        assert "מאיפה אתה יוצא?" in contents

    def test_unsupported_intent_still_extracts_locations(self):
        """Unsupported fields (כלב, 2 נוסעים) don't break extraction."""
        with self._mock_groq({
            "pickup_name": "באר שבע",
            "destination_name": "אילת",
            "departure_time": None,
            "search_radius": None,
            "confidence": 0.85,
            "raw_interpretation": "הבנתי: נסיעה מבאר שבע לאילת",
            "needs_clarification": False,
            "missing_fields": [],
            "ambiguity_reasons": ["הבקשה כוללת תנאים שלא נתמכים"],
            "follow_up_question": None,
        }):
            result = parse_ride_search_query(
                "טרמפ ל-2 נוסעים עם כלב מבאר שבע לאילת"
            )

        assert result.pickup_name == "באר שבע"
        assert result.destination_name == "אילת"
        assert len(result.ambiguity_reasons) > 0
