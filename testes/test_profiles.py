"""
Tests for voice profiles module.

Tests the 3 pre-defined voice profiles (FAST_CPU, BALANCED_CPU, NOISY_ROOM)
and profile loading/application logic.
"""

from __future__ import annotations

import os
import pytest

from jarvis.interface.infra.profiles import (
    PROFILES,
    load_profile,
    apply_profile,
)


class TestProfileStructure:
    """Test profile definitions and structure."""

    def test_profiles_exist(self) -> None:
        """Test that all 3 profiles are defined."""
        assert "fast_cpu" in PROFILES
        assert "balanced_cpu" in PROFILES
        assert "noisy_room" in PROFILES

    def test_profile_has_required_fields(self) -> None:
        """Test that each profile has required fields."""
        required_fields = {
            "name",
            "silence_ms",
            "min_speech_ms",
            "pre_roll_ms",
            "post_roll_ms",
            "vad_aggressiveness",
            "stt_model",
        }
        for profile_name, profile in PROFILES.items():
            for field in required_fields:
                assert field in profile, f"Profile {profile_name} missing field {field}"

    def test_fast_cpu_profile(self) -> None:
        """Test FAST_CPU profile parameters."""
        profile = PROFILES["fast_cpu"]
        assert profile["name"] == "fast_cpu"
        assert profile["silence_ms"] == 400
        assert profile["min_speech_ms"] == 300
        assert profile["pre_roll_ms"] == 100
        assert profile["post_roll_ms"] == 100
        assert profile["vad_aggressiveness"] == 3
        assert profile["stt_model"] == "tiny"

    def test_balanced_cpu_profile(self) -> None:
        """Test BALANCED_CPU profile parameters."""
        profile = PROFILES["balanced_cpu"]
        assert profile["name"] == "balanced_cpu"
        assert profile["silence_ms"] == 600
        assert profile["min_speech_ms"] == 400
        assert profile["pre_roll_ms"] == 150
        assert profile["post_roll_ms"] == 150
        assert profile["vad_aggressiveness"] == 2
        assert profile["stt_model"] == "small"

    def test_noisy_room_profile(self) -> None:
        """Test NOISY_ROOM profile parameters."""
        profile = PROFILES["noisy_room"]
        assert profile["name"] == "noisy_room"
        assert profile["silence_ms"] == 800
        assert profile["min_speech_ms"] == 500
        assert profile["pre_roll_ms"] == 200
        assert profile["post_roll_ms"] == 200
        assert profile["vad_aggressiveness"] == 1
        assert profile["stt_model"] == "small"


class TestLoadProfile:
    """Test load_profile() function."""

    def test_default_loads_balanced_cpu(self) -> None:
        """Test that default profile is balanced_cpu."""
        old_env = os.environ.copy()
        try:
            # Clear JARVIS_VOICE_PROFILE if set
            if "JARVIS_VOICE_PROFILE" in os.environ:
                del os.environ["JARVIS_VOICE_PROFILE"]

            profile = load_profile()
            assert profile["name"] == "balanced_cpu"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_env_var_override(self) -> None:
        """Test that JARVIS_VOICE_PROFILE env var is respected."""
        old_env = os.environ.copy()
        try:
            os.environ["JARVIS_VOICE_PROFILE"] = "fast_cpu"
            profile = load_profile()
            assert profile["name"] == "fast_cpu"

            os.environ["JARVIS_VOICE_PROFILE"] = "noisy_room"
            profile = load_profile()
            assert profile["name"] == "noisy_room"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_parameter_override_env_var(self) -> None:
        """Test that parameter overrides env var."""
        old_env = os.environ.copy()
        try:
            os.environ["JARVIS_VOICE_PROFILE"] = "balanced_cpu"
            profile = load_profile("fast_cpu")
            assert profile["name"] == "fast_cpu"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_invalid_profile_raises_error(self) -> None:
        """Test that invalid profile name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid profile"):
            load_profile("invalid_profile")

    def test_case_insensitive(self) -> None:
        """Test that profile names are case-insensitive."""
        old_env = os.environ.copy()
        try:
            os.environ["JARVIS_VOICE_PROFILE"] = "FAST_CPU"
            profile = load_profile()
            assert profile["name"] == "fast_cpu"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_profile_is_copy(self) -> None:
        """Test that returned profile is a copy (not reference)."""
        profile1 = load_profile("fast_cpu")
        profile2 = load_profile("fast_cpu")
        profile1["silence_ms"] = 999
        assert profile2["silence_ms"] == 400  # Original unchanged


class TestApplyProfile:
    """Test apply_profile() function."""

    def test_apply_profile_sets_env_vars(self) -> None:
        """Test that apply_profile sets environment variables."""
        old_env = os.environ.copy()
        try:
            # Clear all relevant vars first
            for key in [
                "JARVIS_VAD_SILENCE_MS",
                "JARVIS_MIN_AUDIO_SECONDS",
                "JARVIS_VAD_PRE_ROLL_MS",
                "JARVIS_VAD_POST_ROLL_MS",
                "JARVIS_VAD_AGGRESSIVENESS",
                "JARVIS_STT_MODEL",
            ]:
                if key in os.environ:
                    del os.environ[key]

            profile = load_profile("fast_cpu")
            apply_profile(profile)

            assert os.environ.get("JARVIS_VAD_SILENCE_MS") == "400"
            assert os.environ.get("JARVIS_MIN_AUDIO_SECONDS") == "0.3"
            assert os.environ.get("JARVIS_VAD_PRE_ROLL_MS") == "100"
            assert os.environ.get("JARVIS_VAD_POST_ROLL_MS") == "100"
            assert os.environ.get("JARVIS_VAD_AGGRESSIVENESS") == "3"
            assert os.environ.get("JARVIS_STT_MODEL") == "tiny"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_explicit_env_vars_not_overridden(self) -> None:
        """Test that already-set env vars are not overridden."""
        old_env = os.environ.copy()
        try:
            # Set explicit values
            os.environ["JARVIS_VAD_AGGRESSIVENESS"] = "0"
            os.environ["JARVIS_STT_MODEL"] = "base"

            # Clear others
            for key in [
                "JARVIS_VAD_SILENCE_MS",
                "JARVIS_MIN_AUDIO_SECONDS",
                "JARVIS_VAD_PRE_ROLL_MS",
                "JARVIS_VAD_POST_ROLL_MS",
            ]:
                if key in os.environ:
                    del os.environ[key]

            profile = load_profile("fast_cpu")
            apply_profile(profile)

            # Explicit values should be preserved
            assert os.environ.get("JARVIS_VAD_AGGRESSIVENESS") == "0"
            assert os.environ.get("JARVIS_STT_MODEL") == "base"

            # Other values should be set from profile
            assert os.environ.get("JARVIS_VAD_SILENCE_MS") == "400"
            assert os.environ.get("JARVIS_VAD_PRE_ROLL_MS") == "100"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_apply_balanced_cpu_profile(self) -> None:
        """Test applying balanced_cpu profile."""
        old_env = os.environ.copy()
        try:
            # Clear all relevant vars
            for key in [
                "JARVIS_VAD_SILENCE_MS",
                "JARVIS_MIN_AUDIO_SECONDS",
                "JARVIS_VAD_PRE_ROLL_MS",
                "JARVIS_VAD_POST_ROLL_MS",
                "JARVIS_VAD_AGGRESSIVENESS",
                "JARVIS_STT_MODEL",
            ]:
                if key in os.environ:
                    del os.environ[key]

            profile = load_profile("balanced_cpu")
            apply_profile(profile)

            assert os.environ.get("JARVIS_VAD_SILENCE_MS") == "600"
            assert os.environ.get("JARVIS_MIN_AUDIO_SECONDS") == "0.4"
            assert os.environ.get("JARVIS_VAD_AGGRESSIVENESS") == "2"
            assert os.environ.get("JARVIS_STT_MODEL") == "small"
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_apply_noisy_room_profile(self) -> None:
        """Test applying noisy_room profile."""
        old_env = os.environ.copy()
        try:
            # Clear all relevant vars
            for key in [
                "JARVIS_VAD_SILENCE_MS",
                "JARVIS_MIN_AUDIO_SECONDS",
                "JARVIS_VAD_PRE_ROLL_MS",
                "JARVIS_VAD_POST_ROLL_MS",
                "JARVIS_VAD_AGGRESSIVENESS",
                "JARVIS_STT_MODEL",
            ]:
                if key in os.environ:
                    del os.environ[key]

            profile = load_profile("noisy_room")
            apply_profile(profile)

            assert os.environ.get("JARVIS_VAD_SILENCE_MS") == "800"
            assert os.environ.get("JARVIS_MIN_AUDIO_SECONDS") == "0.5"
            assert os.environ.get("JARVIS_VAD_AGGRESSIVENESS") == "1"
            assert os.environ.get("JARVIS_STT_MODEL") == "small"
        finally:
            os.environ.clear()
            os.environ.update(old_env)


class TestProfileIntegration:
    """Integration tests for profiles."""

    def test_load_and_apply_workflow(self) -> None:
        """Test typical load + apply workflow."""
        old_env = os.environ.copy()
        try:
            # Clear env
            for key in [
                "JARVIS_VOICE_PROFILE",
                "JARVIS_VAD_SILENCE_MS",
                "JARVIS_MIN_AUDIO_SECONDS",
                "JARVIS_VAD_PRE_ROLL_MS",
                "JARVIS_VAD_POST_ROLL_MS",
                "JARVIS_VAD_AGGRESSIVENESS",
                "JARVIS_STT_MODEL",
            ]:
                if key in os.environ:
                    del os.environ[key]

            # Set profile via env var
            os.environ["JARVIS_VOICE_PROFILE"] = "fast_cpu"

            # Load and apply
            profile = load_profile()
            apply_profile(profile)

            # Verify
            assert profile["name"] == "fast_cpu"
            assert os.environ.get("JARVIS_VAD_AGGRESSIVENESS") == "3"
            assert os.environ.get("JARVIS_STT_MODEL") == "tiny"
        finally:
            os.environ.clear()
            os.environ.update(old_env)
