# Export Manager Spec

## Purpose
Saves converted ASCII art output into various file formats or system clipboard.

## Requirements
| ID | Requirement |
|----|-------------|
| EX-5.1 | The export manager MUST support exporting to TXT, HTML, SVG, PNG, and copying to system Clipboard. |

## Scenarios
### Scenario: HTML export styling
- GIVEN converted ASCII characters
- WHEN the HTML exporter runs
- THEN it outputs a valid HTML file embedded with styling that matches original dimensions.
