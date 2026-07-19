# Video Exporter Specification

## Purpose

Encode sequences of ASCII-rendered frames into playable video files.

## Requirements

### Requirement: Video Exporter writes MP4 and GIF

The Video Exporter MUST write ASCII frame sequences to MP4 and GIF files.

#### Scenario: MP4 export

- GIVEN a sequence of ASCII-rendered frames and an output path ending in `.mp4`
- WHEN the Video Exporter writes the output
- THEN it produces a playable MP4 file with the requested frame rate and dimensions

#### Scenario: GIF export

- GIVEN a sequence of ASCII-rendered frames and an output path ending in `.gif`
- WHEN the Video Exporter writes the output
- THEN it produces a valid GIF file

### Requirement: Video Exporter accepts frame parameters

The Video Exporter MUST accept frame dimensions, frames per second, and a codec hint.

#### Scenario: Configure FPS and resolution

- GIVEN frames of 640x480 and `--fps 30`
- WHEN the exporter writes the output
- THEN the resulting video plays at 30 FPS and preserves the frame dimensions

### Requirement: Video Exporter releases resources

The Video Exporter MUST release all native video writer resources after writing or on failure.

#### Scenario: Successful cleanup

- GIVEN a frame sequence is written successfully
- WHEN the write operation completes
- THEN the output file is closed and no process holds a write lock

#### Scenario: Empty frame sequence

- GIVEN an empty frame sequence
- WHEN the exporter writes the output
- THEN it raises an error and releases any allocated writer

### Requirement: Video Exporter honors cancellation

The Video Exporter SHOULD stop encoding when the conversion worker signals cancellation.

#### Scenario: Cancel mid-export

- GIVEN a long frame sequence
- WHEN the worker signals cancel
- THEN the exporter stops encoding and closes the output file
