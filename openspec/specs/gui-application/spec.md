# GUI Application Spec

## Purpose
PySide6 user interface for configuring settings, managing execution, and viewing outputs. Supports static images, video, webcam preview, and color output.

## Requirements
| ID | Requirement |
|----|-------------|
| GUI-4.1 | The GUI MUST feature a load pane, draggable split-preview slider, monospace editor panel, progress bar, ETA, and worker cancellation. It MUST support a color mode checkbox, background color dropdown (Black, White, Transparent), QTextEdit HTML rendering for colored output, and a colored preview. It MUST expose save buttons for TXT, HTML, SVG, and PNG exports, and a webcam preview mode. |
| GUI-4.2 | The GUI worker MUST delegate per-frame conversion to `ConversionEngine.convert()`. |
| GUI-4.3 | The GUI code MUST be split into `widgets.py`, `rendering.py`, `style.py`, and `main_window.py`, and `app.py` MUST remain under 200 lines. |
| GUI-4.4 | The worker thread MUST emit a result signal that includes the `char_matrix` field for the GUI to consume. |

## Scenarios
### Scenario: User cancels active processing
- GIVEN an active conversion worker thread running in the GUI
- WHEN the user clicks the cancel button
- THEN the worker thread MUST halt immediately and progress indicator resets.

### Scenario: Color mode toggle preview
- GIVEN GUI with color mode checked
- WHEN a conversion runs
- THEN the comparison preview displays colored characters on the selected background.

### Scenario: Save button writes HTML
- GIVEN a completed conversion with color mode on
- WHEN the user clicks the HTML save button
- THEN a valid HTML file is written through the shared ExportManager

### Scenario: Webcam preview mode
- GIVEN a connected camera
- WHEN the user starts the webcam preview
- THEN the preview panel shows live ASCII frames and the camera releases on stop

### Scenario: Single image conversion
- GIVEN a single image loaded in the GUI
- WHEN the conversion runs
- THEN the worker calls `ConversionEngine.convert()` for the frame

### Scenario: Video conversion
- GIVEN a video loaded in the GUI
- WHEN the conversion runs
- THEN the worker calls `ConversionEngine.convert()` for each frame yielded by the provider

### Scenario: Entry point wiring
- GIVEN `app.py`
- WHEN it imports the four modules
- THEN it is under 200 lines and only wires the application together

### Scenario: Module imports
- GIVEN the GUI package
- WHEN each module is imported
- THEN it succeeds without circular imports

### Scenario: Result signal data
- GIVEN a completed conversion
- WHEN the worker emits the result signal
- THEN the signal payload includes the `char_matrix` field
