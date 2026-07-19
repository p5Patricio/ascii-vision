# Configuration Manager Spec

## Purpose
Loads and saves configuration parameters and preset definitions.

## Requirements
| ID | Requirement |
|----|-------------|
| CF-6.1 | The config manager MUST support JSON-based loading and saving of presets, including color mode, background color, and quantization settings. |
| CF-6.2 | The system SHALL fallback to JetBrains Mono with a non-blocking notification if the requested font is missing. |

## Scenarios
### Scenario: Preset load with missing font
- GIVEN a JSON preset requesting a font not installed on the system
- WHEN the configuration is loaded
- THEN the manager falls back to JetBrains Mono and issues a non-blocking notification.

### Scenario: Save color configurations
- GIVEN active settings with color mode enabled and a custom background
- WHEN config is saved
- THEN settings are serialized into a JSON profile.

### Scenario: Load color configurations
- GIVEN a JSON profile with color settings
- WHEN config is loaded
- THEN application state updates with color mode, background, and quantization settings.
