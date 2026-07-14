# Metrics Evaluation Spec

## Purpose
Computes visual similarity between source image blocks and target glyph patterns.

## Requirements
| ID | Requirement |
|----|-------------|
| MT-3.1 | The evaluation module MUST support MSE (Mean Squared Error), SSIM (Structural Similarity), and Brightness mapping algorithms. |

## Scenarios
### Scenario: Visual matching using SSIM
- GIVEN a source block and a list of glyph candidates
- WHEN metrics evaluation is run with SSIM
- THEN it outputs the structural similarity score for each candidate to select the closest visual match.
