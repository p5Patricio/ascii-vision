import os
import json
import warnings

class ConfigManager:
    """
    Manages loading, saving, and validating ASCII conversion configuration profiles.
    Includes fallback logic for font path resolution.
    """
    DEFAULT_FONT_RELATIVE_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"

    def __init__(self, config_data: dict = None):
        """
        Initializes the ConfigManager with default values or custom config data.
        """
        self.config = self.get_default_config()
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
            "preprocessing": {
                "brightness": 1.0,
                "contrast": 1.0,
                "sharpening": 0.0,
                "gaussian_blur": 0.0
            }
        }

    def resolve_font_path(self, font_path: str) -> str:
        """
        Checks font path availability. If missing, falls back to the bundled 
        JetBrains Mono font and issues a non-blocking RuntimeWarning.
        """
        # If font_path exists, return it
        if font_path and os.path.exists(font_path):
            return font_path

        # Locate the bundled JetBrainsMono-Regular.ttf in assets/fonts/
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(package_dir))
        bundled_font = os.path.abspath(os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Regular.ttf"))

        if os.path.exists(bundled_font):
            warnings.warn(
                f"Font path '{font_path}' not found. Falling back to bundled JetBrains Mono: {bundled_font}",
                RuntimeWarning
            )
            return bundled_font

        # Fallback to local path relative to current working directory
        local_fallback = os.path.abspath(self.DEFAULT_FONT_RELATIVE_PATH)
        warnings.warn(
            f"Font path '{font_path}' not found. Falling back to default relative path: {local_fallback}",
            RuntimeWarning
        )
        return local_fallback

    def validate_config(self, config: dict) -> bool:
        """
        Validates configuration dictionary structure.
        """
        required_keys = {"font_path", "font_size", "charset", "preset", "metric", "preprocessing"}
        if not required_keys.issubset(config.keys()):
            return False
        
        preproc = config["preprocessing"]
        preproc_keys = {"brightness", "contrast", "sharpening", "gaussian_blur"}
        if not isinstance(preproc, dict) or not preproc_keys.issubset(preproc.keys()):
            return False
            
        return True

    def set_config(self, config_data: dict) -> None:
        """
        Sets the configuration values, applying font resolution logic.
        """
        if not self.validate_config(config_data):
            raise ValueError("Invalid configuration data structure.")
        
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
