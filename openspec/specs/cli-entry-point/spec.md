# CLI Entry Point Specification

## Purpose

Provide a headless command-line interface for converting images to ASCII art using the same engine as the GUI.

## Requirements

### Requirement: CLI accepts input and output paths

The CLI MUST accept `--input` and `--output` arguments and produce a valid ASCII export file at the output path.

#### Scenario: Single image conversion

- GIVEN a valid image file
- WHEN `ascii-vision --input image.png --output out.html` is run
- THEN the CLI exits with code 0 and writes a valid HTML file to `out.html`

#### Scenario: Missing input argument

- GIVEN no `--input` argument
- WHEN the CLI is run
- THEN it exits with a non-zero code and prints a usage error

### Requirement: CLI supports output formats

The CLI MUST support TXT, HTML, SVG, and PNG output formats, selected by output extension or an explicit `--format` argument.

#### Scenario: Format by extension

- GIVEN a PNG image and output path `out.svg`
- WHEN the CLI runs
- THEN it writes a valid SVG file

#### Scenario: Explicit format override

- GIVEN output path `out.txt` and `--format html`
- WHEN the CLI runs
- THEN it writes HTML content to the path

### Requirement: CLI installation

The CLI MUST be exposed as an `ascii-vision` console script through `pyproject.toml` and support `python -m ascii_vision`.

#### Scenario: Console script execution

- GIVEN the package is installed
- WHEN `ascii-vision --help` is run
- THEN it prints help text and exits with code 0

#### Scenario: Module execution

- GIVEN the package is installed
- WHEN `python -m ascii_vision --help` is run
- THEN it prints help text and exits with code 0

### Requirement: CLI handles errors gracefully

The CLI MUST report errors to stderr and exit with a non-zero code when input is invalid or output cannot be written.

#### Scenario: Invalid image

- GIVEN a corrupt or non-image file as input
- WHEN the CLI runs
- THEN it exits with a non-zero code and prints an error message

#### Scenario: Unwritable output path

- GIVEN an output path in a non-existent directory
- WHEN the CLI runs
- THEN it exits with a non-zero code and prints an error message
