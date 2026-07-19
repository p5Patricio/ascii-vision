import os
import json
import warnings
from pathlib import Path

import jsonschema
from platformdirs import user_config_dir

# Supported TrueType / OpenType font extensions.
VALID_FONT_EXTENSIONS = (".ttf", ".otf")


class ConfigManager:
    """
    Manages loading, saving, and validating ASCII conversion configuration profiles.
    Includes fallback logic for font path resolution and named profile CRUD.
    """
    DEFAULT_FONT_RELATIVE_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"

    def __init__(self, config_data: dict = None, profiles_dir: Path = None):
        """
        Initializes the ConfigManager with default values or custom config data.

        Args:
            config_data: Optional initial config dict to apply.
            profiles_dir: Optional explicit profiles directory path.
                          Defaults to ``platformdirs`` user config dir.
        """
        self.config = self.get_default_config()
        self._profiles_dir = Path(profiles_dir) if profiles_dir else None
        if config_data:
            self.set_config(config_data)

    @classmethod
    def get_default_config(cls) -> dict:
        """
        Returns the default configuration dict.
        """
        return {
            "font_path": cls.DEFAULT_FONT_RELATIVE_PATH,
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
                "gaussian_blur": 0.0
            }
        }

    def resolve_font_path(self, font_path: str) -> str:
        """
        Checks font path availability. If missing or invalid, falls back to the
        bundled JetBrains Mono font and issues a non-blocking RuntimeWarning.

        Validation includes checking that the file exists, is readable, and
        has a ``.ttf`` or ``.otf`` extension.
        """
        # --- Validate extension --------------------------------------------------
        if font_path:
            ext = os.path.splitext(font_path)[1].lower()
            if ext not in VALID_FONT_EXTENSIONS:
                warnings.warn(
                    f"Font path '{font_path}' has unsupported extension '{ext}'. "
                    f"Expected {VALID_FONT_EXTENSIONS}. Falling back to bundled font.",
                    RuntimeWarning
                )
                font_path = None  # force fallback

        # --- If a valid path exists, return it ------------------------------------
        if font_path and os.path.exists(font_path) and os.access(font_path, os.R_OK):
            return font_path

        # --- Fallback: bundled JetBrains Mono ------------------------------------
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(package_dir))
        bundled_font = os.path.abspath(os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Regular.ttf"))

        if os.path.exists(bundled_font):
            warnings.warn(
                f"Font path '{font_path}' not found or invalid. Falling back to bundled JetBrains Mono: {bundled_font}",
                RuntimeWarning
            )
            return bundled_font

        # --- Last-resort fallback: relative to CWD --------------------------------
        local_fallback = os.path.abspath(self.DEFAULT_FONT_RELATIVE_PATH)
        warnings.warn(
            f"Font path '{font_path}' not found. Falling back to default relative path: {local_fallback}",
            RuntimeWarning
        )
        return local_fallback

    def _load_schema(self) -> dict | None:
        """
        Loads config_schema.json from the package directory, if present.
        Returns the parsed schema dict, or None if the file is unavailable.
        """
        schema_path = Path(__file__).resolve().parent / "config_schema.json"
        if schema_path.is_file():
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _validate_with_schema(self, config: dict) -> None:
        """
        Validates the config dict against ``config_schema.json``.

        Raises ``jsonschema.ValidationError`` when validation fails.
        Falls back to ``validate_config()`` only when the schema file is missing.
        """
        schema = self._load_schema()
        if schema is None:
            if not self.validate_config(config):
                raise ValueError("Invalid configuration data structure.")
            return

        jsonschema.validate(instance=config, schema=schema)

    def validate_config(self, config: dict) -> bool:
        """
        Validates configuration dictionary structure.
        """
        required_keys = {
            "font_path", "font_size", "charset", "preset", "metric", "preprocessing",
            "color_mode", "background_color"
        }
        if not required_keys.issubset(config.keys()):
            return False
        
        if not isinstance(config.get("color_mode"), bool):
            return False
        if not isinstance(config.get("background_color"), str):
            return False
        
        preproc = config["preprocessing"]
        preproc_keys = {"brightness", "contrast", "sharpening", "gaussian_blur"}
        if not isinstance(preproc, dict) or not preproc_keys.issubset(preproc.keys()):
            return False
            
        return True

    def set_config(self, config_data: dict) -> None:
        """
        Sets the configuration values, applying font resolution logic.

        Raises ``jsonschema.ValidationError`` if the config does not satisfy
        the JSON Schema (or ``ValueError`` if the schema file is missing and
        the fallback validation fails).
        """
        self._validate_with_schema(config_data)

        # Make a copy and resolve the font path
        new_config = json.loads(json.dumps(config_data))
        new_config["font_path"] = self.resolve_font_path(new_config["font_path"])
        self.config = new_config

    def load(self, filepath: str) -> dict:
        """
        Loads a configuration from a JSON file, validates it, and updates self.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.set_config(data)
        return self.config

    def save(self, filepath: str) -> None:
        """
        Saves the current configuration to a JSON file.
        """
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    # ------------------------------------------------------------------
    # Named profile CRUD
    # ------------------------------------------------------------------

    @property
    def profiles_dir(self) -> Path:
        """
        Returns the directory where named profiles are stored.

        Uses ``platformdirs`` for a cross-platform user config path
        (e.g. ``~/.config/ascii-vision/profiles/`` on Linux,
        ``%APPDATA%\\ascii-vision\\profiles\\`` on Windows).
        """
        if self._profiles_dir is None:
            self._profiles_dir = Path(user_config_dir("ascii-vision", ensure_exists=True)) / "profiles"
            self._profiles_dir.mkdir(parents=True, exist_ok=True)
        return self._profiles_dir

    def save_profile(self, name: str) -> Path:
        """
        Saves the current active configuration as a named profile.

        Args:
            name: Profile name (used as the file stem).

        Returns:
            The ``Path`` to the saved profile file.
        """
        profile_path = self.profiles_dir / f"{name}.json"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
        return profile_path

    def load_profile(self, name: str) -> dict:
        """
        Loads a named profile, validates it, and applies it as the active config.

        Args:
            name: Profile name (without ``.json`` extension).

        Returns:
            The loaded and validated configuration dict.

        Raises:
            FileNotFoundError: If no profile with that name exists.
        """
        profile_path = self.profiles_dir / f"{name}.json"
        if not profile_path.is_file():
            raise FileNotFoundError(f"Profile '{name}' not found at {profile_path}")

        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.set_config(data)
        return self.config

    def delete_profile(self, name: str) -> None:
        """
        Removes a named profile file.

        No-op if the profile does not exist.
        """
        profile_path = self.profiles_dir / f"{name}.json"
        if profile_path.is_file():
            profile_path.unlink()

    def list_profiles(self) -> list[str]:
        """
        Returns a sorted list of all saved profile names.
        """
        if not self.profiles_dir.is_dir():
            return []
        return sorted(p.stem for p in self.profiles_dir.glob("*.json"))
