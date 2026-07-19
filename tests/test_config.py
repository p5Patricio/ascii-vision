"""Tests for ConfigManager: schema enforcement and profile CRUD."""

import json
import tempfile
from pathlib import Path

import jsonschema
import pytest

from ascii_vision.config import ConfigManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_config() -> dict:
    return {
        "font_path": "assets/fonts/JetBrainsMono-Regular.ttf",
        "font_size": 12,
        "charset": "ascii",
        "preset": "Balanced",
        "metric": "MSE",
        "color_mode": False,
        "background_color": "Black",
        "preprocessing": {
            "brightness": 1.0,
            "contrast": 1.0,
            "sharpening": 0.0,
            "gaussian_blur": 0.0,
        },
    }


@pytest.fixture
def config_with_temp_profiles_dir(valid_config) -> ConfigManager:
    """Returns a ConfigManager with an isolated temp profiles directory."""
    with tempfile.TemporaryDirectory() as tmp:
        cm = ConfigManager(profiles_dir=Path(tmp))
        cm.set_config(valid_config)
        yield cm


# ---------------------------------------------------------------------------
# Schema enforcement  (spec: config-manager)
# ---------------------------------------------------------------------------

class TestSchemaEnforcement:
    """Requirement: Schema enforcement on config."""

    def test_valid_config_accepted(self, valid_config):
        """GIVEN a well-formed JSON config that satisfies the schema
        WHEN set_config is called
        THEN the config is applied without error."""
        cm = ConfigManager()
        cm.set_config(valid_config)
        assert cm.config["font_path"] is not None
        assert cm.config["font_size"] == 12
        assert cm.config["preset"] == "Balanced"

    def test_missing_required_field_raises(self, valid_config):
        """GIVEN a config with a missing required field
        WHEN set_config is called
        THEN a ValidationError is raised and the active config is unchanged."""
        del valid_config["font_size"]
        cm = ConfigManager()
        with pytest.raises(jsonschema.ValidationError):
            cm.set_config(valid_config)

    def test_invalid_preset_raises(self, valid_config):
        """GIVEN a config with an invalid enum value
        WHEN set_config is called
        THEN a ValidationError is raised."""
        valid_config["preset"] = "NonExistentPreset"
        cm = ConfigManager()
        with pytest.raises(jsonschema.ValidationError):
            cm.set_config(valid_config)

    def test_invalid_background_color_raises(self, valid_config):
        """GIVEN a config with an invalid background_color
        WHEN set_config is called
        THEN a ValidationError is raised."""
        valid_config["background_color"] = "NeonGreen"
        cm = ConfigManager()
        with pytest.raises(jsonschema.ValidationError):
            cm.set_config(valid_config)

    def test_schema_loaded_at_init(self, valid_config):
        """GIVEN the ConfigManager initializes
        WHEN it loads config_schema.json
        THEN the schema is available for all subsequent validations."""
        cm = ConfigManager()
        schema = cm._load_schema()
        assert schema is not None
        assert schema["title"] == "AsciiVisionConfig"
        assert "$defs" in schema
        assert "profile" in schema["$defs"]

    def test_active_config_unchanged_on_invalid(self, valid_config):
        """THEN the active config is unchanged after a failed validation."""
        cm = ConfigManager()
        original_config = dict(cm.config)

        with pytest.raises(jsonschema.ValidationError):
            cm.set_config({"font_path": "test.ttf"})  # missing many fields

        assert cm.config == original_config

    def test_wrong_type_for_color_mode_raises(self, valid_config):
        """GIVEN a config where color_mode is not a boolean
        WHEN set_config is called
        THEN a ValidationError is raised."""
        valid_config["color_mode"] = "yes"
        cm = ConfigManager()
        with pytest.raises(jsonschema.ValidationError):
            cm.set_config(valid_config)


# ---------------------------------------------------------------------------
# Profile CRUD  (spec: export-profiles)
# ---------------------------------------------------------------------------

class TestProfileCRUD:
    """Requirement: Profile CRUD through ConfigManager."""

    def test_save_named_profile(self, config_with_temp_profiles_dir):
        """GIVEN a set of active conversion settings
        WHEN the user saves a profile named 'mydark'
        THEN the profile is persisted and appears in the profile list."""
        cm = config_with_temp_profiles_dir
        cm.save_profile("mydark")
        assert "mydark" in cm.list_profiles()

    def test_load_named_profile(self, config_with_temp_profiles_dir):
        """GIVEN a saved profile named 'mydark'
        WHEN ConfigManager loads it
        THEN all stored settings are applied to the active configuration."""
        cm = config_with_temp_profiles_dir
        cm.save_profile("mydark")

        # Change the active config
        cm.config["preset"] = "Fast"
        assert cm.config["preset"] == "Fast"

        # Load the saved profile back
        loaded = cm.load_profile("mydark")
        assert loaded["preset"] == "Balanced"
        assert loaded["font_size"] == 12
        assert cm.config["preset"] == "Balanced"

    def test_list_available_profiles(self, config_with_temp_profiles_dir):
        """GIVEN three saved profiles
        WHEN profiles are listed
        THEN all three names are returned."""
        cm = config_with_temp_profiles_dir
        cm.save_profile("profile_a")
        cm.config["preset"] = "Fast"
        cm.save_profile("profile_b")
        cm.config["preset"] = "High"
        cm.save_profile("profile_c")

        profiles = cm.list_profiles()
        assert len(profiles) == 3
        assert "profile_a" in profiles
        assert "profile_b" in profiles
        assert "profile_c" in profiles

    def test_delete_profile(self, config_with_temp_profiles_dir):
        """GIVEN a saved profile named 'mydark'
        WHEN the profile is deleted
        THEN it no longer appears in the profile list."""
        cm = config_with_temp_profiles_dir
        cm.save_profile("mydark")
        assert "mydark" in cm.list_profiles()

        cm.delete_profile("mydark")
        assert "mydark" not in cm.list_profiles()

    def test_delete_nonexistent_profile_is_noop(self, config_with_temp_profiles_dir):
        """Deleting a profile that does not exist should not raise."""
        cm = config_with_temp_profiles_dir
        cm.delete_profile("does_not_exist")  # should not raise
        assert cm.list_profiles() == []

    def test_profile_round_trip_preserves_all_fields(self, config_with_temp_profiles_dir):
        """GIVEN a config with all fields set
        WHEN saved and loaded
        THEN every field matches exactly."""
        cm = config_with_temp_profiles_dir
        cm.save_profile("full_roundtrip")

        # Modify active config drastically
        cm.config["preset"] = "Max"
        cm.config["metric"] = "SSIM"
        cm.config["color_mode"] = True
        cm.config["background_color"] = "White"

        loaded = cm.load_profile("full_roundtrip")
        assert loaded["preset"] == "Balanced"
        assert loaded["metric"] == "MSE"
        assert loaded["color_mode"] is False
        assert loaded["background_color"] == "Black"

    def test_load_nonexistent_profile_raises(self, config_with_temp_profiles_dir):
        """GIVEN no saved profile named 'missing'
        WHEN load_profile is called
        THEN a FileNotFoundError is raised."""
        cm = config_with_temp_profiles_dir
        with pytest.raises(FileNotFoundError):
            cm.load_profile("missing")

    def test_profiles_dir_uses_platformdirs_by_default(self):
        """The default profiles_dir uses platformdirs user_config_dir."""
        cm = ConfigManager()
        path = cm.profiles_dir
        assert "ascii-vision" in str(path)
        assert path.suffix != ".json"  # it's a directory

    def test_list_profiles_when_empty(self):
        """GIVEN no saved profiles
        WHEN list_profiles is called
        THEN an empty list is returned."""
        with tempfile.TemporaryDirectory() as tmp:
            cm = ConfigManager(profiles_dir=Path(tmp))
            assert cm.list_profiles() == []
