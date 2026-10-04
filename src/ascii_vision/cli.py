import argparse
import os
import sys

import numpy as np

from ascii_vision import __version__
from ascii_vision.config import ConfigManager
from ascii_vision.engine import ConversionEngine
from ascii_vision.exporter import ExportManager
from ascii_vision.frame_provider import (
    BatchFrameProvider,
    FrameProvider,
    StaticImageFrameProvider,
    VideoFrameProvider,
)
from ascii_vision.glyph_cache import GlyphCache
from ascii_vision.video_exporter import VideoExporter

# File extensions treated as video sources.
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".gif", ".ogv"}


# Canonical option names. Matching is case-insensitive; the GUI's preset names
# ("High Quality", "Maximum Quality") are accepted alongside the short ones.
PRESET_CHOICES = ("Fast", "Balanced", "High", "High Quality", "Max", "Maximum Quality", "Custom")
METRIC_CHOICES = ("Brightness", "MSE", "SSIM")
BACKGROUND_CHOICES = ("Black", "White", "Transparent")

# Fallback values used when neither the command line nor a profile gives one.
DEFAULT_COLUMNS = 100
DEFAULT_FPS = 30


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a whole number") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1 (got {number})")
    return number


def _choice_of(choices: tuple[str, ...]):
    """argparse ``type`` that maps any capitalisation onto the canonical name."""
    lookup = {c.lower(): c for c in choices}

    def convert(value: str) -> str:
        canonical = lookup.get(value.strip().lower())
        if canonical is None:
            raise argparse.ArgumentTypeError(
                f"invalid choice '{value}' (choose from {', '.join(choices)})"
            )
        return canonical

    return convert


def build_parser() -> argparse.ArgumentParser:
    """
    Builds the argparse parser for the ``ascii-vision`` CLI.

    Options that a profile can also set default to ``None`` so that a profile is
    only overridden by flags the user actually typed.
    """
    parser = argparse.ArgumentParser(
        prog="ascii-vision",
        description="Convert images and videos to ASCII art from the command line.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--input", help="Path to the input image or video.")
    parser.add_argument("--output", help="Path for the output file.")
    parser.add_argument(
        "--format",
        help=(
            "Output format override. If omitted, the format is inferred from "
            "the output file extension."
        ),
    )
    parser.add_argument(
        "--columns",
        type=_positive_int,
        default=None,
        help=f"Number of ASCII columns to generate (default: {DEFAULT_COLUMNS}).",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        default=None,
        help="Enable color mode and preserve per-cell colors in the output.",
    )
    parser.add_argument(
        "--preset",
        type=_choice_of(PRESET_CHOICES),
        default=None,
        help="Conversion preset: " + ", ".join(PRESET_CHOICES) + " (default: Balanced).",
    )
    parser.add_argument(
        "--metric",
        type=_choice_of(METRIC_CHOICES),
        default=None,
        help="Similarity metric: Brightness, MSE, SSIM. Defaults to preset choice.",
    )
    parser.add_argument(
        "--charset",
        default=None,
        help="Character set preset (ascii, shades, blocks, braille) or a custom string (default: ascii).",
    )
    parser.add_argument(
        "--font-size",
        type=_positive_int,
        default=None,
        help="Font size used for PNG, HTML, and SVG output (default: 12).",
    )
    parser.add_argument(
        "--background",
        type=_choice_of(BACKGROUND_CHOICES),
        default=None,
        help="Background color: Black, White, Transparent (default: Black).",
    )
    parser.add_argument(
        "--fps",
        type=_positive_int,
        default=None,
        help="Frames per second for video output (default: same as the input video).",
    )
    parser.add_argument(
        "--font-path",
        default=None,
        help="Path to a TrueType font. Falls back to the bundled font if omitted.",
    )
    # --- Profile flags ---
    parser.add_argument(
        "--profile",
        default=None,
        help="Load settings from a named export profile.",
    )
    parser.add_argument(
        "--save-profile",
        default=None,
        metavar="NAME",
        help="Save the active settings as a named export profile and exit.",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print all saved profile names and exit.",
    )
    # --- Batch processing flags ---
    parser.add_argument(
        "--input-glob",
        default=None,
        help="Glob pattern for batch processing multiple input files.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Enable recursive glob matching with ``**`` patterns (requires --input-glob).",
    )
    return parser


def _resolve_settings(args: argparse.Namespace, base_config: dict | None) -> dict:
    """
    Merges defaults, an optional profile and the flags the user typed.

    Precedence (highest first): explicit command-line flag, profile value,
    built-in default.
    """
    config = dict(base_config) if base_config else ConfigManager.get_default_config()

    def pick(flag, key, default):
        return flag if flag is not None else config.get(key, default)

    config.update(
        {
            "font_path": args.font_path or config.get("font_path", ConfigManager.DEFAULT_FONT_RELATIVE_PATH),
            "font_size": pick(args.font_size, "font_size", 12),
            "charset": pick(args.charset, "charset", "ascii"),
            "preset": pick(args.preset, "preset", "Balanced"),
            "metric": pick(args.metric, "metric", "MSE"),
            "color_mode": bool(pick(args.color, "color_mode", False)),
            "background_color": pick(args.background, "background_color", "Black"),
            "columns": pick(args.columns, "columns", DEFAULT_COLUMNS),
        }
    )
    return config


def _resolve_font_name(font_path: str) -> str:
    """
    Returns a reasonable font family name for HTML/SVG exports.
    """
    base = os.path.splitext(os.path.basename(font_path))[0]
    if base:
        return base.replace("-", " ").replace("_", " ")
    return "monospace"


def _create_provider(input_path: str) -> FrameProvider:
    """
    Creates a ``FrameProvider`` for the input path.

    Video files are routed through ``VideoFrameProvider``; everything else is
    treated as a static image.
    """
    ext = os.path.splitext(input_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return VideoFrameProvider(input_path)
    return StaticImageFrameProvider(input_path)


def _render_frame(
    char_matrix: np.ndarray,
    color_matrix: np.ndarray | None,
    font_path: str,
    font_size: int,
    bg_color: str,
) -> np.ndarray:
    """
    Renders a character matrix to an RGB NumPy image using the PNG exporter.
    """
    from ascii_vision.exporter import to_png
    img = to_png(char_matrix, font_path, font_size, color_matrix, bg_color)
    return np.array(img.convert("RGB"))


def _build_engine(config: dict) -> ConversionEngine:
    """
    Builds a ``ConversionEngine`` from the resolved configuration.
    """
    glyph_cache = GlyphCache(
        font_path=config["font_path"],
        font_size=config["font_size"],
        charset=config["charset"],
    )
    engine = ConversionEngine(
        glyph_cache,
        metric=config["metric"],
        preset=config["preset"],
        preprocessing=config["preprocessing"],
    )
    engine.invert = str(config.get("background_color", "")).lower() == "white"
    return engine


def _resolve_output_format(output_path: str, explicit_format: str | None) -> str:
    """
    Normalizes the target format from the explicit flag or the file extension.
    """
    if explicit_format:
        return explicit_format.lower().lstrip(".")
    return os.path.splitext(output_path)[1].lower().lstrip(".")


def _is_directory_output(output_path: str) -> bool:
    """
    Heuristic: is ``--output`` meant to be a directory path?

    Returns ``True`` when the path already exists as a directory *or* when it
    ends with a path separator (e.g. ``./out/`` on Linux / ``.\\out\\`` on
    Windows).
    """
    if os.path.isdir(output_path):
        return True
    return output_path.endswith(os.sep) or output_path.endswith("/")


def _batch_output_path(
    input_path: str, preset: str, output_dir: str, fmt: str
) -> str:
    """
    Derives a batch output path following the ``{stem}_{preset}.{ext}`` scheme.
    """
    stem = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(output_dir, f"{stem}_{preset}.{fmt}")


def _run_batch(
    args: argparse.Namespace,
    base_config: dict | None,
) -> int:
    """
    Execute the batch processing loop.

    Expands ``--input-glob`` via ``BatchFrameProvider``, iterates over every
    matched file, derives the output path per the naming scheme, and delegates
    to ``run_conversion()`` for each file.

    Returns an exit code suitable for ``sys.exit()``.
    """
    # --- Safety: --recursive without --input-glob ----------------------------
    if args.recursive and not args.input_glob:
        print(
            "ascii-vision: error: --recursive requires --input-glob",
            file=sys.stderr,
        )
        return 1

    # --- Expand glob ---------------------------------------------------------
    provider = BatchFrameProvider(args.input_glob, recursive=args.recursive)
    files = provider.get_files()

    if not files:
        print(f"No files matching '{args.input_glob}' found.", file=sys.stderr)
        return 1

    # --- Resolve output behaviour --------------------------------------------
    if not args.output:
        print(
            "ascii-vision: error: --output is required for batch processing",
            file=sys.stderr,
        )
        return 1

    is_dir = _is_directory_output(args.output)

    if not is_dir and len(files) > 1:
        print(
            "ascii-vision: error: --output must be a directory when"
            " processing multiple files",
            file=sys.stderr,
        )
        return 1

    if is_dir:
        # --- Directory output: derive per-file names -------------------------
        os.makedirs(args.output, exist_ok=True)
        fmt = args.format if args.format else "html"
        preset_name = args.preset or (base_config or {}).get("preset") or "Balanced"
        preset_slug = preset_name.replace(" ", "_")

        processed = 0
        for input_file in files:
            output_path = _batch_output_path(
                input_file, preset_slug, args.output, fmt
            )
            file_args = argparse.Namespace(**vars(args))
            file_args.input = input_file
            file_args.output = output_path
            try:
                run_conversion(file_args, base_config=base_config)
                processed += 1
            except (Exception, KeyboardInterrupt) as exc:
                print(f"Error processing {input_file}: {exc}", file=sys.stderr)

        if processed == 0:
            return 1
        return 0

    # --- Single output path with exactly one file ----------------------------
    file_args = argparse.Namespace(**vars(args))
    file_args.input = files[0]
    run_conversion(file_args, base_config=base_config)
    return 0


def _run_image_output(
    provider: FrameProvider,
    engine: ConversionEngine,
    config: dict,
    output_path: str,
    fmt: str | None,
) -> str:
    """
    Converts every input frame and saves the final ASCII result to a file.
    """
    manager = ExportManager()
    last_char_matrix = None
    last_color_matrix = None

    for frame in provider.get_frames():
        result = engine.convert(frame, cols=config["columns"], color_mode=config["color_mode"])
        if config["color_mode"] and isinstance(result, tuple):
            last_char_matrix, last_color_matrix = result
        else:
            last_char_matrix = result
            last_color_matrix = None

    if last_char_matrix is None:
        raise ValueError("No frames were loaded from the input source.")

    return manager.save(
        last_char_matrix,
        output_path,
        font_name=_resolve_font_name(config["font_path"]),
        font_size=config["font_size"],
        color_matrix=last_color_matrix,
        bg_color=config["background_color"],
        format=fmt,
        font_path=config["font_path"],
    )


def _run_video_output(
    provider: FrameProvider,
    engine: ConversionEngine,
    config: dict,
    output_path: str,
    fps: int | None,
    source_path: str | None = None,
) -> str:
    """
    Converts every input frame to ASCII and writes a video of the rendered frames.

    The output keeps the input's frame rate (unless *fps* is given) and, for
    video inputs, its audio track.
    """
    exporter = VideoExporter()
    if fps is None:
        source_fps = getattr(provider, "fps", 0.0)
        fps = int(round(source_fps)) if source_fps else DEFAULT_FPS
    is_video_source = isinstance(provider, VideoFrameProvider)

    def ascii_frames():
        for frame in provider.get_frames():
            result = engine.convert(frame, cols=config["columns"], color_mode=config["color_mode"])
            if config["color_mode"] and isinstance(result, tuple):
                char_matrix, color_matrix = result
            else:
                char_matrix = result
                color_matrix = None
            yield _render_frame(
                char_matrix,
                color_matrix,
                config["font_path"],
                config["font_size"],
                config["background_color"],
            )

    exporter.write(
        ascii_frames(), output_path, fps=fps,
        source_audio=source_path if is_video_source else None,
    )
    return output_path


def run_conversion(args: argparse.Namespace, base_config: dict | None = None) -> str:
    """
    Executes the conversion pipeline for the parsed CLI arguments.

    Args:
        args: Parsed CLI arguments.
        base_config: Optional starting config (e.g. from a loaded profile).
                     If omitted, defaults are used as a base.

    Returns the output path on success.
    """
    cm = ConfigManager()
    cm.set_config(_resolve_settings(args, base_config))
    config = cm.config

    provider = _create_provider(args.input)
    try:
        engine = _build_engine(config)
        # The glyph cache may have swapped in a fallback font that covers the
        # character set (e.g. Braille); render the output with that same font.
        config["font_path"] = engine.glyph_cache.font_path

        output_format = _resolve_output_format(args.output, args.format)
        if output_format in VideoExporter.SUPPORTED_FORMATS:
            return _run_video_output(provider, engine, config, args.output, args.fps, args.input)
        return _run_image_output(provider, engine, config, args.output, args.format)
    finally:
        provider.cleanup()


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns an exit code suitable for ``sys.exit()``.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    cm = ConfigManager()

    # --- Profile-only operations (no input/output needed) ---
    if args.list_profiles:
        profiles = cm.list_profiles()
        if profiles:
            print("\n".join(profiles))
        else:
            print("No saved profiles found.")
        return 0

    if args.save_profile:
        try:
            ConfigManager.validate_profile_name(args.save_profile)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        # Start from the profile named by --profile (if any) so flags tweak it.
        starting_point = None
        if args.profile:
            try:
                cm.load_profile(args.profile)
                starting_point = cm.config
            except FileNotFoundError:
                print(f"Error: Profile '{args.profile}' not found.", file=sys.stderr)
                return 1
            except Exception as exc:
                print(f"Error: Could not load profile '{args.profile}': {exc}", file=sys.stderr)
                return 1
        cm.set_config(_resolve_settings(args, starting_point))
        cm.save_profile(args.save_profile)
        print(f"Profile '{args.save_profile}' saved.")
        return 0

    # --- Profile check (before input/output validation) ---
    base_config = None
    if args.profile:
        try:
            cm.load_profile(args.profile)
            base_config = cm.config
        except FileNotFoundError:
            print(f"Error: Profile '{args.profile}' not found.", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Error: Could not load profile '{args.profile}': {exc}", file=sys.stderr)
            return 1

    # --- Batch processing path ---
    if args.input_glob:
        return _run_batch(args, base_config)

    # --- Single-file conversion path ---
    if not args.input or not args.output:
        parser.print_usage()
        print("ascii-vision: error: the following arguments are required: --input, --output")
        return 1

    try:
        run_conversion(args, base_config=base_config)
        return 0
    except (Exception, KeyboardInterrupt, SystemExit) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
