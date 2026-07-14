# GUI Application Spec

## Purpose
PySide6 user interface for configuring settings, managing execution, and viewing outputs.

## Requirements
| ID | Requirement |
|----|-------------|
| GUI-4.1 | The GUI MUST feature a load pane, draggable split-preview slider, monospace editor panel, progress bar, ETA, and worker cancellation. |

## Scenarios
### Scenario: User cancels active processing
- GIVEN an active conversion worker thread running in the GUI
- WHEN the user clicks the cancel button
- THEN the worker thread MUST halt immediately and progress indicator resets.
