import os
import sys
import tempfile

import numpy as np
import pytest
from PIL import Image

from ascii_vision.cli import build_parser, main


TEST_FONT_PATH = "assets/fonts/JetBrainsMono-Regular.ttf"


@pytest.fixture
def sample_image():
    """Yields the path to a small RGB test image."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sample.png")
        Image.new("RGB", (30, 20), color="red").save(path)
        yield path


class TestCliArgumentParsing:
    def test_cli_help_exits_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_cli_missing_input_exits_nonzero(self):
        exit_code = main([])
        assert exit_code == 1

    def test_build_parser_accepts_missing_input(self):
        """--input and --output are no longer parser-required to allow profile-only operations."""
        parser = build_parser()
        args = parser.parse_args(["--output", "out.txt"])
        assert args.output == "out.txt"
        assert args.input is None


class TestCliImageConversion:
    def test_cli_single_image_html(self, sample_image):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.html")
            assert main(["--input", sample_image, "--output", output]) == 0
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<html>" in content

    def test_cli_format_by_extension(self, sample_image):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.svg")
            assert main(["--input", sample_image, "--output", output]) == 0
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<svg" in content
            assert "</svg>" in content

    def test_cli_format_override_argument(self, sample_image):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.txt")
            assert main(["--input", sample_image, "--output", output, "--format", "html"]) == 0
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<html>" in content
            assert "<pre>" in content


class TestCliErrorHandling:
    def test_cli_invalid_image_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_input = os.path.join(tmpdir, "bad.png")
            with open(bad_input, "w", encoding="utf-8") as f:
                f.write("not an image")
            output = os.path.join(tmpdir, "out.html")
            assert main(["--input", bad_input, "--output", output]) != 0

    def test_cli_unwritable_output_exits_nonzero(self, sample_image):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "no_such_dir", "out.html")
            assert main(["--input", sample_image, "--output", output]) != 0
            assert not os.path.exists(output)

    def test_cli_unsupported_format_override_exits_nonzero(self, sample_image):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "out.txt")
            assert main(["--input", sample_image, "--output", output, "--format", "pdf"]) != 0


class TestCliBatchProcessing:
    """Batch processing tests (``--input-glob`` and ``--recursive``)."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_png(self, path: str, size: tuple[int, int] = (10, 10)) -> None:
        """Create a small solid-colour PNG at *path*."""
        Image.new("RGB", size, color="red").save(path)

    def _batch_main(
        self, tmpdir: str, glob_pattern: str, *,
        recursive: bool = False, preset: str | None = None,
    ) -> int:
        """Run ``main()`` with batch args inside *tmpdir*."""
        out_dir = os.path.join(tmpdir, "out")
        os.makedirs(out_dir, exist_ok=True)
        args = ["--input-glob", glob_pattern, "--output", out_dir]
        if recursive:
            args.append("--recursive")
        if preset:
            args.extend(["--preset", preset])
        return main(args)

    # ------------------------------------------------------------------
    # Scenario: Basic glob expansion
    # ------------------------------------------------------------------
    def test_basic_glob_expansion(self):
        """Only files matching the glob pattern are processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_png(os.path.join(tmpdir, "a.png"))
            self._make_png(os.path.join(tmpdir, "b.png"))
            self._make_png(os.path.join(tmpdir, "c.jpg"))

            exit_code = self._batch_main(tmpdir, os.path.join(tmpdir, "*.png"))
            assert exit_code == 0
            out_files = os.listdir(os.path.join(tmpdir, "out"))
            assert len(out_files) == 2

    # ------------------------------------------------------------------
    # Scenario: No matches
    # ------------------------------------------------------------------
    def test_no_matches_exits_nonzero(self):
        """A glob that matches nothing exits non-zero."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_png(os.path.join(tmpdir, "a.png"))
            exit_code = self._batch_main(tmpdir, os.path.join(tmpdir, "*.tiff"))
            assert exit_code != 0

    # ------------------------------------------------------------------
    # Scenario: Recursive match
    # ------------------------------------------------------------------
    def test_recursive_matches_subdirs(self):
        """``--recursive`` enables ``**`` patterns for subdirectory matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "sub")
            os.makedirs(sub)
            self._make_png(os.path.join(sub, "a.png"))

            pattern = os.path.join(tmpdir, "**", "*.png")
            exit_code = self._batch_main(tmpdir, pattern, recursive=True)
            assert exit_code == 0
            out_files = os.listdir(os.path.join(tmpdir, "out"))
            assert len(out_files) == 1

    # ------------------------------------------------------------------
    # Scenario: Recursive without glob
    # ------------------------------------------------------------------
    def test_recursive_without_glob_exits_nonzero(self):
        """``--recursive`` without ``--input-glob`` exits non-zero."""
        exit_code = main(["--recursive"])
        assert exit_code != 0

    # ------------------------------------------------------------------
    # Scenario: Single output with multiple inputs
    # ------------------------------------------------------------------
    def test_single_output_with_multiple_inputs_exits_nonzero(self):
        """A file ``--output`` with multiple glob matches exits non-zero."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_png(os.path.join(tmpdir, "a.png"))
            self._make_png(os.path.join(tmpdir, "b.png"))

            single_out = os.path.join(tmpdir, "single.html")
            exit_code = main([
                "--input-glob", os.path.join(tmpdir, "*.png"),
                "--output", single_out,
            ])
            assert exit_code != 0

    # ------------------------------------------------------------------
    # Scenario: Output naming correctness
    # ------------------------------------------------------------------
    def test_output_naming_contains_stem_and_preset(self):
        """Batch output files follow the ``{stem}_{preset}.{ext}`` scheme."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_png(os.path.join(tmpdir, "testimg.png"))
            self._make_png(os.path.join(tmpdir, "other.png"))

            exit_code = self._batch_main(
                tmpdir, os.path.join(tmpdir, "*.png"), preset="Fast",
            )
            assert exit_code == 0

            out_dir = os.path.join(tmpdir, "out")
            out_files = os.listdir(out_dir)
            assert any("testimg_Fast" in f for f in out_files)
            assert any("other_Fast" in f for f in out_files)
            assert all(f.endswith(".html") for f in out_files)


