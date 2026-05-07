from __future__ import annotations

from pathlib import Path

from multi_agent_daily_report.config import (
    expand_path,
    load_config,
    merge_dicts,
    write_default_config,
)


def test_expand_path_home():
    result = expand_path("~/test")
    assert str(result) == str(Path.home() / "test")


def test_expand_path_absolute():
    result = expand_path("/tmp/test")
    assert str(result.resolve()) == str(Path("/tmp/test").resolve())


def test_merge_dicts_shallow():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = merge_dicts(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_merge_dicts_nested():
    base = {"parent": {"x": 1, "y": 2}}
    override = {"parent": {"y": 3, "z": 4}}
    result = merge_dicts(base, override)
    assert result == {"parent": {"x": 1, "y": 3, "z": 4}}


def test_merge_dicts_non_dict_override():
    base = {"parent": {"x": 1}}
    override = {"parent": "replaced"}
    result = merge_dicts(base, override)
    assert result == {"parent": "replaced"}


def test_write_default_config_creates_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    result = write_default_config(config_path)
    assert result == config_path
    assert config_path.exists()


def test_load_config_defaults_when_missing(tmp_path):
    config_path = tmp_path / "nonexistent.yaml"
    config = load_config(config_path)
    assert config["sources"]["claude"]["enabled"] is True
    assert config["output"]["timezone"] == "Asia/Shanghai"
