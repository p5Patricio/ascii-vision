# Frame Provider Spec

## Purpose
A generic stream abstraction to retrieve frames from source media, supporting static images, video files, and live webcam feeds.

## Requirements
| ID | Requirement |
|----|-------------|
| FR-1.1 | Under static image inputs, the provider MUST return exactly one frame. |
| FR-1.2 | The provider SHALL expose a standard generator interface for frame-by-frame retrieval. |
| FR-1.3 | The VideoFrameProvider MUST open a video file and yield every frame through the standard generator interface. |
| FR-1.4 | The WebcamFrameProvider MUST open the default camera and yield live frames through the standard generator interface. |
| FR-1.5 | All providers MUST stop yielding when the conversion worker signals cancellation. |
| FR-1.6 | All providers MUST release native capture resources when exhausted, cancelled, or on error. |

## Scenarios
### Scenario: Static image frame retrieval
- GIVEN a static image input
- WHEN frame retrieval is requested
- THEN the provider returns exactly one frame and terminates the generator.

### Scenario: Iteration yields frames
- GIVEN a provider instance
- WHEN the caller iterates over it
- THEN it yields frames one at a time until exhausted

### Scenario: Video file iteration
- GIVEN a valid video file
- WHEN a caller iterates over VideoFrameProvider
- THEN it yields each frame in order until the video ends

### Scenario: Video file end of stream
- GIVEN a valid video file
- WHEN the last frame is yielded
- THEN the generator terminates cleanly and releases the video source

### Scenario: Live camera feed
- GIVEN the default camera is available
- WHEN a caller iterates over WebcamFrameProvider
- THEN it yields consecutive live frames until stopped

### Scenario: Camera not available
- GIVEN no camera is connected
- WHEN WebcamFrameProvider is instantiated
- THEN it raises an error and does not yield frames

### Scenario: Cancel video processing
- GIVEN a long video file
- WHEN the worker signals cancel
- THEN the provider stops yielding frames and releases the video source

### Scenario: Video cleanup
- GIVEN a video provider that has yielded frames
- WHEN the generator is closed or exhausted
- THEN the video source is released and no file lock remains
