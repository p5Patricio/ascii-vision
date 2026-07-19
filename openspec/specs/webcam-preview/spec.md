# Webcam Preview Specification

## Purpose

Display a live ASCII preview from the default camera without blocking the GUI.

## Requirements

### Requirement: Webcam Preview opens the default camera

The Webcam Preview MUST open the default camera device and yield frames through a standard generator interface.

#### Scenario: Start preview

- GIVEN the GUI is running
- WHEN the user starts the webcam preview
- THEN the default camera opens and frames begin to flow

#### Scenario: No camera available

- GIVEN no camera is connected
- WHEN the user starts the preview
- THEN it raises an error and does not block the GUI

### Requirement: Webcam Preview runs off the GUI thread

The Webcam Preview MUST run in a background worker and emit frames via Qt signals.

#### Scenario: Frame signal emission

- GIVEN the preview is active
- WHEN a new camera frame is captured
- THEN the worker emits a Qt signal carrying the rendered pixmap

### Requirement: Webcam Preview releases resources

The Webcam Preview MUST release the camera on stop, window close, and error.

#### Scenario: Stop preview

- GIVEN the preview is active
- WHEN the user clicks stop
- THEN the camera is released and frame emission stops

#### Scenario: Window close

- GIVEN the preview is active
- WHEN the main window closes
- THEN the camera is released

### Requirement: Webcam Preview uses performance defaults

The Webcam Preview SHOULD use the Fast preset, Brightness metric, and a small column count by default.

#### Scenario: Default settings

- GIVEN the preview is started without custom settings
- WHEN the first frame is rendered
- THEN the worker uses Fast preset, Brightness metric, and a small column count
