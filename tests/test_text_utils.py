from __future__ import annotations

from multi_agent_daily_report.text_utils import (
    compact_text,
    encoded_project_path,
    is_noise_text,
)


def test_compact_text_string():
    assert compact_text("hello world") == "hello world"


def test_compact_text_truncation():
    result = compact_text("a" * 600, limit=500)
    assert len(result) == 500


def test_compact_text_none():
    assert compact_text(None) == ""


def test_compact_text_list_of_dicts():
    result = compact_text([{"text": "hello"}, {"content": "world"}])
    assert "hello" in result
    assert "world" in result


def test_compact_text_dict():
    assert compact_text({"text": "hello"}) == "hello"


def test_is_noise_text_empty():
    assert is_noise_text("") is True
    assert is_noise_text("   ") is True


def test_is_noise_text_api_error():
    assert is_noise_text("API Error: something") is True


def test_is_noise_text_valid():
    assert is_noise_text("fixed the config loader") is False


def test_encoded_project_path_normal():
    assert encoded_project_path("my-project") == "my-project"


def test_encoded_project_path_dash_prefix():
    assert (
        encoded_project_path("-Users-wjy777-work-space") == "/Users/wjy777/work/space"
    )
