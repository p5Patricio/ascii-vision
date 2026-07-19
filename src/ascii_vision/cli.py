import argparse
import os
import sys
from typing import Optional

import numpy as np

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


def build_parser() -> argparse.ArgumentParser:
    """
    Builds the argparse parser for the ``ascii-vision`` CLI.
    """
    parser = argparse.ArgumentParser(
        prog="ascii-vision",
        description="Convert images and videos to ASCII art from the command line.",
    )
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
        type=int,
        default=100,
        help="Number of ASCII columns to generate (default: 100).",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="Enable color mode and preserve per-cell colors in the output.",
    )
    parser.add_argument(
        "--preset",
        default="Balanced",
        help="Conversion preset: Fast, Balanced, High, Max (default: Balanced).",
    )
    parser.add_argument(
        "--metric",
        default=None,
        help="Similarity metric: Brightness, MSE, SSIM. Defaults to preset choice.",
    )
    parser.add_argument(
        "--charset",
        default="ascii",
        help="Character set preset or custom string (default: ascii).",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=12,
        help="Font size used for PNG, HTML, and SVG output (default: 12).",
    )
    parser.add_argument(
        "--background",
        default="Black",
        help="Background color: Black, White, Transparent (default: Black).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second for video output (default: 30).",
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
    color_matrix: Optional[np.ndarray],
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
    return ConversionEngine(
        glyph_cache,
        metric=config["metric"],
        preset=config["preset"],
        preprocessing=config["preprocessing"],
    )


def _resolve_output_format(output_path: str, explicit_format: Optional[str]) -> str:
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
        preset_slug = args.preset.replace(" ", "_")

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
    fmt: Optional[str],
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
    fps: int,
) -> str:
    """
    Converts every input frame to ASCII and writes a video of the rendered frames.
    """
    exporter = VideoExporter()

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

    exporter.write(ascii_frames(), output_path, fps=fps)
    return output_path


def run_conversion(args: argparse.Namespace, base_config: Optional[dict] = None) -> str:
    """
    Executes the conversion pipeline for the parsed CLI arguments.

    Args:
        args: Parsed CLI arguments.
        base_config: Optional starting config (e.g. from a loaded profile).
                     If omitted, defaults are used as a base.

    Returns the output path on success.
    """
    config = dict(base_config) if base_config else ConfigManager().get_default_config()
    # CLI args override any existing (profile or default) values
    config.update(
        {
            "font_path": args.font_path if args.font_path else config.get("font_path", ConfigManager.DEFAULT_FONT_RELATIVE_PATH),
            "font_size": args.font_size,
            "charset": args.charset,
            "preset": args.preset,
            "metric": args.metric if args.metric else config["metric"],
            "color_mode": args.color,
            "background_color": args.background,
            "columns": args.columns,
        }
    )

    cm = ConfigManager()
    cm.set_config(config)
    config = cm.config

    provider = _create_provider(args.input)
    engine = _build_engine(config)

    try:
        output_format = _resolve_output_format(args.output, args.format)
        if output_format in VideoExporter.SUPPORTED_FORMATS:
            return _run_video_output(provider, engine, config, args.output, args.fps)
        return _run_image_output(provider, engine, config, args.output, args.format)
    finally:
        provider.cleanup()


def main(argv: Optional[list[str]] = None) -> int:
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
        config = cm.get_default_config()
        config.update(
            {
                "font_path": args.font_path if args.font_path else ConfigManager.DEFAULT_FONT_RELATIVE_PATH,
                "font_size": args.font_size,
                "charset": args.charset,
                "preset": args.preset,
                "metric": args.metric if args.metric else config["metric"],
                "color_mode": args.color,
                "background_color": args.background,
                "columns": args.columns,
            }
        )
        cm.set_config(config)
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
