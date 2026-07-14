# Conversion Engine Spec

## Purpose
Core pipeline that prepares images, resizes, corrects aspect ratios, and performs block-matching against a pre-rendered glyph cache.

## Requirements
| ID | Requirement |
|----|-------------|
| CV-2.1 | The engine MUST adjust image dimensions automatically based on font metrics or via manual override. |
| CV-2.2 | The engine MUST maintain a pre-rendered glyph cache for the active monospace font to optimize comparison. |

## Scenarios
### Scenario: Aspect ratio correction and conversion
- GIVEN a source image and selected monospace font
- WHEN conversion is executed
- THEN dimensions are adjusted to match font metrics, and blocks are mapped to cached glyphs.
