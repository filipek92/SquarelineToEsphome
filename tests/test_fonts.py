"""Tests for font handling and inclusion of symbols into ESPHome YAML."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from squareline_to_esphome.__main__ import main


def _write_fcfg(target_path: Path, *, codename: str = "Other", symbols: str = "°čá") -> None:
    data = {
        "codename": codename,
        "ttf_path": "/assets/fonts/Montserrat-SemiBold.ttf",
        "bin_path": "/assets/ui_font_Other.bin",
        "c_path": "/assets/ui_font_Other.c",
        "cfg_path": "/assets/ui_font_Other.fcfg",
        "size": 20,
        "bpp": 2,
        "letters": 0,
        "ranges": ["0x20-0x7f"],
        "symbols": symbols,
        "customparams": "--no-compress --no-prefilter",
        "uploaded": False,
    }
    target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.usefixtures("sample_project_path")
def test_font_symbols_are_emitted(sample_project_path: Path):
    project_root = sample_project_path.parent
    fonts_dir = project_root / "assets" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    # Create a temporary .fcfg with special symbols
    fcfg_path = fonts_dir / "ui_font_Other.fcfg"
    _write_fcfg(fcfg_path)

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        test_args = [
            "squareline-to-esphome",
            str(sample_project_path),
            "-o",
            str(output_path),
        ]
        with patch("sys.argv", test_args):
            with patch("pyperclip.copy"):
                main()

        # Load YAML and verify font glyphs contain our symbols
        yaml_data = yaml.safe_load(Path(output_path).read_text(encoding="utf-8"))

        assert "font" in yaml_data, "Font section should be present when .fcfg exists"
        fonts = yaml_data["font"]
        assert isinstance(fonts, list) and len(fonts) > 0

        font_other = next((f for f in fonts if f.get("id") == "Other"), None)
        assert font_other is not None, "Expected font with id 'Other' from .fcfg"

        glyphs = font_other.get("glyphs")
        assert glyphs is not None, "glyphs should be generated from symbols field"
        for ch in ["°", "č", "á"]:
            assert ch in glyphs, f"Expected symbol '{ch}' in generated glyphs"

    finally:
        # Cleanup files
        if fcfg_path.exists():
            fcfg_path.unlink()
        # The output file is in a temp dir and will be auto-removed by system, but try to delete
        try:
            output_path.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
