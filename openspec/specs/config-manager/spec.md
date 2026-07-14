# Configuration Manager Spec

## Purpose
Loads and saves configuration parameters and preset definitions.

## Requirements
| ID | Requirement |
|----|-------------|
| CF-6.1 | The config manager MUST support JSON-based loading and saving of presets. |
| CF-6.2 | The system SHALL fallback to JetBrains Mono with a non-blocking notification if the requested font is missing. |

## Scenarios
### Scenario: Preset load with missing font
- GIVEN a JSON preset requesting a font not installed on the system
- WHEN the configuration is loaded
- THEN the manager falls back to JetBrains Mono and issues a non-blocking notification.
