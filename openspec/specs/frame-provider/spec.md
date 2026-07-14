# Frame Provider Spec

## Purpose
A generic stream abstraction to retrieve frames from source media.

## Requirements
| ID | Requirement |
|----|-------------|
| FR-1.1 | Under static image inputs, the provider MUST return exactly one frame. |
| FR-1.2 | The provider SHALL expose a standard generator interface for frame-by-frame retrieval. |

## Scenarios
### Scenario: Static image frame retrieval
- GIVEN a static image input
- WHEN frame retrieval is requested
- THEN the provider returns exactly one frame and terminates the generator.
