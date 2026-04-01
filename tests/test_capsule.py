"""Tests for core/capsule.py — Capsule Runtime + YAML Loader.

Written BEFORE implementation (TDD Red Phase).
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

FIXTURES = Path(__file__).parent / "fixtures" / "capsules"


class TestLoadCapsule:
    def test_load_valid_yaml(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok_123"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        assert cap.config.id == "test_capsule"
        assert cap.config.name == "Test Bot"
        assert cap.config.owner_name == "Test Owner"
        assert cap.config.owner_telegram_id == 123456789
        assert cap.config.model == "sonnet"

    def test_env_var_resolution(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "resolved_token_abc"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        assert cap.config.bot_token == "resolved_token_abc"

    def test_missing_required_field(self):
        from neura.core.capsule import Capsule
        with pytest.raises(ValueError, match="id"):
            Capsule.load("bad_missing_id", config_dir=str(FIXTURES))

    def test_defaults_applied(self):
        """Minimal YAML — optional fields get defaults."""
        from neura.core.capsule import Capsule
        cap = Capsule.load("minimal", config_dir=str(FIXTURES))
        assert cap.config.model == "sonnet"
        assert cap.config.effort == "standard"
        assert isinstance(cap.config.skills, list)
        assert isinstance(cap.config.employees, list)
        assert cap.config.bot_token == "raw-token-no-env"

    def test_file_not_found(self):
        from neura.core.capsule import Capsule
        with pytest.raises(FileNotFoundError):
            Capsule.load("nonexistent_capsule", config_dir=str(FIXTURES))


class TestLoadAll:
    def test_load_all(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            capsules = Capsule.load_all(config_dir=str(FIXTURES))
        assert isinstance(capsules, dict)
        assert "test_capsule" in capsules
        assert "minimal" in capsules
        assert len(capsules) >= 3  # test_capsule, minimal, trial_capsule


class TestGetEngineConfig:
    def test_converts_to_engine_config(self):
        from neura.core.capsule import Capsule
        from neura.core.engine import EngineConfig
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        ecfg = cap.get_engine_config()
        assert isinstance(ecfg, EngineConfig)
        assert ecfg.model == "sonnet"
        assert "Read" in ecfg.allowed_tools
        assert ecfg.home_dir is not None  # auto-computed


class TestIsEmployee:
    def test_owner_is_employee(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        assert cap.is_employee(123456789) is True

    def test_staff_is_employee(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        assert cap.is_employee(987654321) is True

    def test_stranger_is_not_employee(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        assert cap.is_employee(999999999) is False


class TestGetSystemPrompt:
    def test_reads_system_md(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        prompt = cap.get_system_prompt()
        assert "Test Bot" in prompt
        assert "helpful" in prompt


class TestTrialExpired:
    def test_trial_disabled(self):
        from neura.core.capsule import Capsule
        with patch.dict(os.environ, {"TEST_BOT_TOKEN": "tok"}):
            cap = Capsule.load("test_capsule", config_dir=str(FIXTURES))
        assert cap.is_trial_expired() is False  # trial disabled = not expired

    def test_trial_expired(self):
        """Trial started 2026-03-20, 5 days → expired by 2026-04-01."""
        from neura.core.capsule import Capsule
        cap = Capsule.load("trial_capsule", config_dir=str(FIXTURES))
        assert cap.is_trial_expired() is True  # 12 days ago, trial was 5 days
