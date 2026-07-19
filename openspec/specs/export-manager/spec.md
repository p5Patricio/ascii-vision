# Export Manager Spec

## Purpose
Saves converted ASCII art output into various file formats or system clipboard. Provides a shared `save()` dispatcher used by both CLI and GUI.

## Requirements
| ID | Requirement |
|----|-------------|
| EX-5.1 | The export manager MUST support exporting to TXT, HTML, SVG, PNG, and copying to system Clipboard. When color mode is active: HTML export MUST use RLE-grouped spans; SVG export MUST use RLE-grouped tspans; PNG export MUST draw text in colors with custom background; TXT/Clipboard MUST use 24-bit ANSI escape codes. The export manager MUST expose a single `save()` dispatcher that CLI and GUI share. |
| EX-5.2 | The `save()` dispatcher MUST select the exporter by output extension or an explicit `format` argument. |
| EX-5.3 | The `save()` dispatcher MUST return the output path on success and raise a descriptive exception on failure. |
| EX-5.4 | The export manager MUST be importable from the headless package without pulling in GUI dependencies. |

## Scenarios
### Scenario: HTML export styling
- GIVEN converted ASCII characters
- WHEN the HTML exporter runs
- THEN it outputs a valid HTML file embedded with styling that matches original dimensions.

### Scenario: Color RLE HTML export
- GIVEN color-mode ASCII output
- WHEN HTML exporter runs
- THEN it outputs HTML with RLE-grouped colored spans.

### Scenario: Color PNG export
- GIVEN color-mode ASCII and custom background
- WHEN PNG exporter runs
- THEN it renders colored text on the background.

### Scenario: CLI and GUI share save dispatcher
- GIVEN the same conversion result
- WHEN the CLI calls `save()` and the GUI calls `save()`
- THEN both produce identical output files for the same format and settings

### Scenario: Format auto-detected from extension
- GIVEN output path `out.svg`
- WHEN `save()` is called without an explicit format
- THEN it writes SVG output

### Scenario: Format override argument
- GIVEN output path `out.txt` and `format="html"`
- WHEN `save()` is called
- THEN it writes HTML content

### Scenario: Successful save
- GIVEN a valid conversion result and writable path
- WHEN `save()` runs
- THEN it returns the output path

### Scenario: Unwritable path
- GIVEN an output path in a non-existent directory
- WHEN `save()` runs
- THEN it raises an exception and does not create a partial file

### Scenario: Import without Qt
- GIVEN a Python environment without PySide6
- WHEN `from ascii_vision.exporter import ExportManager` is executed
- THEN it succeeds without importing Qt modules
